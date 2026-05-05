from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from app.schemas.impact import ResourceImpact
from app.schemas.intent import ToolCallIntent

_SECRET_ENV_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)
_PRIVATE_IP_PATTERN = re.compile(r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)")
_HTTP_UPLOAD_FLAG_PATTERN = re.compile(
    r"\s(?:-d|--data|--data-raw|--data-binary|-F|--form|-T|--upload-file)\b",
    re.IGNORECASE,
)
_HTTP_DOWNLOAD_FLAG_PATTERN = re.compile(r"\s(?:-O|-o|--output)\b", re.IGNORECASE)
_HTTP_METHOD_FLAG_PATTERN = re.compile(r"(?:-X|--request)\s+([A-Za-z]+)")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_RESOURCES_PATH = PROJECT_ROOT / "configs" / "rules" / "sensitive_resources.yaml"


class ResourceImpactService:
    def __init__(self) -> None:
        self._detectors = self._load_detector_config()

    def assess(self, intent: ToolCallIntent, arguments: dict) -> ResourceImpact:
        effect_type = "tool_execute"
        impact_level = "medium"
        mutation_risk = False
        exfiltration_risk = False
        sensitivity = "internal"
        reason_parts: list[str] = []
        impact_signals: list[str] = []
        signal_details: dict[str, Any] = {}
        domain_trust_level: str | None = None

        command_text = self._extract_command_text(arguments)
        payload_text = self._extract_payload_text(arguments)
        combined_text = f"{command_text} {payload_text}".strip().lower()
        is_secret_context = self._contains_secret_marker(combined_text)

        if intent.action_type == "file_read":
            effect_type = "read"
            impact_level = "low"
            resource_id = intent.target_resource_id
            if ".." in resource_id or resource_id.startswith("/"):
                impact_level = "high"
                impact_signals.append("workspace_scope_violation")
                reason_parts.append("path_out_of_workspace")
        elif intent.action_type == "env_read":
            effect_type = "env_read"
            sensitivity = "secret" if _SECRET_ENV_PATTERN.search(intent.target_resource_id) else "sensitive"
            impact_level = "high" if sensitivity == "secret" else "medium"
            impact_signals.append("environment_variable_access")
            reason_parts.append("environment_variable_access")
            if sensitivity == "secret":
                impact_signals.append("secret_accessed")
        elif intent.action_type == "http":
            effect_type = self._classify_http_effect(arguments=arguments, command_text=command_text)
            impact_level = "medium"
            url = str(
                arguments.get("url")
                or arguments.get("target_url")
                or arguments.get("endpoint")
                or intent.target_resource_id
                or ""
            ).strip()
            method = self._extract_http_method(arguments=arguments, command_text=command_text)
            domain_trust_level = self._classify_domain_trust(url)
            signal_details["url"] = url
            signal_details["http_method"] = method or "GET"
            signal_details["payload_present"] = bool(arguments.get("payload_present")) or bool(payload_text)
            signal_details["domain_trust_level"] = domain_trust_level
            impact_signals.append(f"domain_{domain_trust_level}")

            if effect_type == "upload":
                impact_signals.append("payload_upload")
            elif effect_type == "download":
                impact_signals.append("payload_download")

            if domain_trust_level == "untrusted":
                impact_level = self._max_impact(impact_level, "high")
                reason_parts.append("domain_untrusted")
                if effect_type in {"upload", "http_request"}:
                    impact_signals.append("outbound_to_untrusted_domain")

            combo_signals, combo_exfiltration_risk = self._detect_command_combo_risk(
                command_text=command_text,
                combined_text=combined_text,
            )
            for signal in combo_signals:
                if signal not in impact_signals:
                    impact_signals.append(signal)

            if is_secret_context and effect_type == "upload":
                exfiltration_risk = True
                impact_level = self._max_impact(impact_level, "high")
                impact_signals.append("possible_secret_exfiltration")
                reason_parts.append("possible_sensitive_upload")

            if combo_exfiltration_risk:
                exfiltration_risk = True
                impact_level = self._max_impact(impact_level, "critical")
                reason_parts.append("command_combo_exfiltration_pattern")
        else:
            effect_type = self._classify_shell_effect(command_text)
            combo_signals, combo_exfiltration_risk = self._detect_command_combo_risk(
                command_text=command_text,
                combined_text=combined_text,
            )
            for signal in combo_signals:
                if signal not in impact_signals:
                    impact_signals.append(signal)

            if effect_type == "delete":
                mutation_risk = True
                impact_level = "critical"
                reason_parts.append("delete_operation_detected")
            elif effect_type == "write":
                mutation_risk = True
                impact_level = "high"
                reason_parts.append("write_operation_detected")
            elif effect_type == "execute":
                impact_level = "high"
                reason_parts.append("execute_operation_detected")

            if combo_exfiltration_risk:
                exfiltration_risk = True
                impact_level = self._max_impact(impact_level, "critical")
                reason_parts.append("command_combo_exfiltration_pattern")

        if effect_type in {"execute", "delete", "write"}:
            mutation_risk = True

        if intent.data_direction == "outbound" and effect_type in {"upload", "http_request"} and not exfiltration_risk:
            reason_parts.append("outbound_operation_detected")

        reason = ",".join(self._dedupe(reason_parts or impact_signals)) if (reason_parts or impact_signals) else "baseline_impact_profile"
        return ResourceImpact(
            resource_type=intent.target_resource_type,
            resource_id=intent.target_resource_id,
            sensitivity=sensitivity,
            effect_type=effect_type,
            impact_level=impact_level,
            mutation_risk=mutation_risk,
            exfiltration_risk=exfiltration_risk,
            reason=reason,
            impact_signals=self._dedupe(impact_signals),
            domain_trust_level=domain_trust_level,
            signal_details=signal_details,
        )

    @staticmethod
    def _max_impact(current: str, target: str) -> str:
        levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if levels.get(target, -1) > levels.get(current, -1):
            return target
        return current

    @staticmethod
    def _extract_command_text(arguments: dict[str, Any]) -> str:
        value = arguments.get("command") or arguments.get("cmd") or ""
        return str(value).strip()

    @staticmethod
    def _extract_payload_text(arguments: dict[str, Any]) -> str:
        chunks: list[str] = []
        for key in ("body", "data", "payload", "content", "json", "form", "files"):
            value = arguments.get(key)
            if value in (None, "", {}, []):
                continue
            chunks.append(str(value))
        return " ".join(chunks).strip()

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _contains_secret_marker(self, text: str) -> bool:
        return self._contains_any(text, self._detectors["secret_markers"])

    def _detect_command_combo_risk(self, command_text: str, combined_text: str) -> tuple[list[str], bool]:
        lowered_command = command_text.lower()
        lowered_combined = combined_text.lower()
        secret_accessed = self._contains_secret_marker(lowered_combined)
        outbound = self._contains_any(lowered_command, self._detectors["outbound_tokens"])
        encoded = self._contains_any(lowered_command, self._detectors["encode_tokens"])
        compressed = self._contains_any(lowered_command, self._detectors["compress_tokens"])

        signals: list[str] = []
        if secret_accessed:
            signals.append("secret_accessed")
        if outbound:
            signals.append("command_outbound")
        if encoded:
            signals.append("payload_encoded")
        if compressed:
            signals.append("payload_compressed")

        high_risk_combo = secret_accessed and outbound and (encoded or compressed)
        medium_risk_combo = secret_accessed and outbound
        if high_risk_combo:
            signals.append("multi_stage_exfiltration_pattern")
            return signals, True
        if medium_risk_combo:
            signals.append("possible_secret_exfiltration")
            return signals, True
        return signals, False

    @staticmethod
    def _classify_shell_effect(command_text: str) -> str:
        lowered = command_text.lower()
        if any(token in lowered for token in ("rm -rf", " rm ", " del ", "unlink ", "rmdir ")):
            return "delete"
        if any(token in lowered for token in (">", ">>", "tee ", " cp ", " mv ", " sed -i", "truncate ")):
            return "write"
        if any(token in lowered for token in ("bash ", "sh ", "python -c", "node -e", "powershell ", "chmod +x")):
            return "execute"
        return "execute" if lowered else "tool_execute"

    @staticmethod
    def _extract_http_method(arguments: dict[str, Any], command_text: str) -> str | None:
        method = arguments.get("http_method") or arguments.get("method") or arguments.get("verb")
        if isinstance(method, str) and method.strip():
            return method.strip().upper()
        match = _HTTP_METHOD_FLAG_PATTERN.search(command_text or "")
        if match is not None:
            return match.group(1).upper()
        lowered = (command_text or "").lower()
        if "wget " in lowered:
            return "GET"
        if "curl " in lowered:
            return "GET"
        return None

    @staticmethod
    def _has_http_payload(arguments: dict[str, Any], command_text: str) -> bool:
        if bool(arguments.get("payload_present")):
            return True
        if any(arguments.get(key) not in (None, "", {}, []) for key in ("body", "data", "payload", "content", "json", "form", "files")):
            return True
        lowered = command_text.lower()
        return _HTTP_UPLOAD_FLAG_PATTERN.search(lowered) is not None

    def _classify_http_effect(self, arguments: dict[str, Any], command_text: str) -> str:
        method = self._extract_http_method(arguments=arguments, command_text=command_text) or "GET"
        payload_present = self._has_http_payload(arguments=arguments, command_text=command_text)
        lowered = command_text.lower()

        if method in {"POST", "PUT", "PATCH"} or payload_present:
            return "upload"
        if method == "GET":
            if _HTTP_DOWNLOAD_FLAG_PATTERN.search(lowered) is not None:
                return "download"
            return "http_request"
        if method == "DELETE":
            return "http_request"
        return "http_request"

    def _classify_domain_trust(self, url: str) -> str:
        host = self._extract_host(url)
        if not host:
            return "untrusted"
        if self._is_internal_host(host):
            return "internal"
        if self._host_matches(host, self._detectors["trusted_domains"]):
            return "trusted"
        if self._host_matches(host, self._detectors["internal_domains"]):
            return "internal"
        return "untrusted"

    @staticmethod
    def _extract_host(url: str) -> str:
        candidate = (url or "").strip()
        if not candidate:
            return ""
        parsed = urlparse(candidate)
        return (parsed.hostname or "").lower()

    def _is_internal_host(self, host: str) -> bool:
        if host in {"localhost", "127.0.0.1"}:
            return True
        if host.endswith(".local") or host.endswith(".internal"):
            return True
        if _PRIVATE_IP_PATTERN.match(host):
            return True
        try:
            parsed_ip = ipaddress.ip_address(host)
            return parsed_ip.is_private or parsed_ip.is_loopback
        except ValueError:
            return False

    @staticmethod
    def _host_matches(host: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            normalized = pattern.strip().lower()
            if not normalized:
                continue
            if normalized.startswith("*.") and host.endswith(normalized[1:]):
                return True
            if host == normalized or host.endswith(f".{normalized}"):
                return True
        return False

    @staticmethod
    def _contains_any(text: str, markers: list[str]) -> bool:
        lowered = text.lower()
        return any(marker.lower() in lowered for marker in markers)

    @staticmethod
    def _load_detector_config() -> dict[str, list[str]]:
        defaults = {
            "trusted_domains": [
                "api.openai.com",
                "github.com",
                "pypi.org",
            ],
            "internal_domains": [
                "localhost",
                "127.0.0.1",
                ".local",
                ".internal",
            ],
            "secret_markers": [
                "@secret",
                "api_key",
                "apikey",
                "token",
                "password",
                "credential",
                "authorization:",
                "bearer ",
            ],
            "outbound_tokens": [
                "curl ",
                "wget ",
                "http ",
                "https://",
                "scp ",
                "sftp ",
                "rsync ",
                "nc ",
                "netcat ",
            ],
            "encode_tokens": [
                "base64",
                "openssl enc",
                "xxd",
            ],
            "compress_tokens": [
                "tar ",
                "zip ",
                "gzip",
                "bzip2",
                "xz ",
            ],
        }

        if not SENSITIVE_RESOURCES_PATH.exists():
            return defaults

        try:
            with SENSITIVE_RESOURCES_PATH.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
        except Exception:
            return defaults

        if not isinstance(loaded, dict):
            return defaults

        domain_trust = loaded.get("domain_trust", {})
        detectors = loaded.get("detectors", {})
        if not isinstance(domain_trust, dict):
            domain_trust = {}
        if not isinstance(detectors, dict):
            detectors = {}

        trusted_domains = domain_trust.get("trusted_domains", defaults["trusted_domains"])
        internal_domains = domain_trust.get("internal_domains", defaults["internal_domains"])
        secret_markers = detectors.get("secret_markers", defaults["secret_markers"])
        outbound_tokens = detectors.get("outbound_tokens", defaults["outbound_tokens"])
        encode_tokens = detectors.get("encode_tokens", defaults["encode_tokens"])
        compress_tokens = detectors.get("compress_tokens", defaults["compress_tokens"])

        return {
            "trusted_domains": [str(v) for v in trusted_domains if str(v).strip()],
            "internal_domains": [str(v) for v in internal_domains if str(v).strip()],
            "secret_markers": [str(v) for v in secret_markers if str(v).strip()],
            "outbound_tokens": [str(v) for v in outbound_tokens if str(v).strip()],
            "encode_tokens": [str(v) for v in encode_tokens if str(v).strip()],
            "compress_tokens": [str(v) for v in compress_tokens if str(v).strip()],
        }


resource_impact_service = ResourceImpactService()
