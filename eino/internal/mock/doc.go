/*
 * Copyright 2024 CloudWeGo Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Package mock provides mock implementations for testing purposes.
//
// This package aims to provide mock implementations for interfaces in the components package,
// making it easier to use in testing environments. It includes mock implementations for
// various core components such as retrievers, tools, message handlers, and graph runners.
//
// Directory Structure:
//   - components/: Contains mock implementations for various components
//   - retriever/: Provides mock implementation for the Retriever interface
//   - retriever_mock.go: Mock implementation for document retrieval
//   - tool/: Mock implementations for tool-related interfaces
//   - message/: Mock implementations for message handling components
//   - graph/: Mock implementations for graph execution components
//   - stream/: Mock implementations for streaming components
//
// Usage:
// These mock implementations are primarily used in unit tests and integration tests,
// allowing developers to conduct tests without depending on actual external services.
// Each mock component strictly follows the contract of its corresponding interface
// while providing controllable behaviors and results.
//
// Examples:
//
//   - Using mock retriever:
//     retriever := mock.NewMockRetriever()
//     // Configure retriever behavior
//
//   - Using mock tool:
//     tool := mock.NewMockTool()
//     // Configure tool behavior
//
//   - Using mock graph runner:
//     runner := mock.NewMockGraphRunner()
//     // Configure runner behavior
package mock
