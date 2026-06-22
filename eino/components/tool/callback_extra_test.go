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

package tool

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestConvCallbackInput(t *testing.T) {
	assert.NotNil(t, ConvCallbackInput(&CallbackInput{}))
	assert.NotNil(t, ConvCallbackInput("asd"))
	assert.Nil(t, ConvCallbackInput(123))
	assert.Nil(t, ConvCallbackInput(nil))
}

func TestConvCallbackOutput(t *testing.T) {
	assert.NotNil(t, ConvCallbackOutput(&CallbackOutput{}))
	assert.NotNil(t, ConvCallbackOutput("asd"))
	assert.Nil(t, ConvCallbackOutput(123))
	assert.Nil(t, ConvCallbackOutput(nil))
}
