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

package gslice

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestToMap(t *testing.T) {
	type Foo struct {
		ID   int
		Name string
	}
	mapper := func(f Foo) (int, string) { return f.ID, f.Name }
	assert.Equal(t, map[int]string{}, ToMap([]Foo{}, mapper))
	assert.Equal(t, map[int]string{}, ToMap(nil, mapper))
	assert.Equal(t,
		map[int]string{1: "one", 2: "two", 3: "three"},
		ToMap([]Foo{{1, "one"}, {2, "two"}, {3, "three"}}, mapper))
}
