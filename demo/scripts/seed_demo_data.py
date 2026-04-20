import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.dependencies import SessionLocal, init_db
from app.services.rule_service import RuleService


def main() -> None:
    settings = get_settings()
    init_db()
    with SessionLocal() as db:
        count = RuleService(db).seed_from_risk_yaml(str(settings.resolve_path(settings.risk_rules_path)))
    print(f"Seeded {count} rules")


if __name__ == "__main__":
    main()
