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

package gmap

import (
	"fmt"
	"sort"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestMerge(t *testing.T) {
	assert.Equal(t, map[int]int{1: 1, 2: 2, 3: 3, 4: 4},
		Concat(map[int]int{1: 1, 2: 2, 3: 3, 4: 4}, nil))
	assert.Equal(t, map[int]int{1: 1, 2: 2, 3: 3, 4: 4},
		Concat[int, int](nil, map[int]int{1: 1, 2: 2, 3: 3, 4: 4}))
	assert.Equal(t, map[int]int{}, Concat[int, int](nil, nil))
	assert.Equal(t, map[int]int{1: 1, 2: 2, 3: 3, 4: 4},
		Concat(map[int]int{1: 1, 2: 2, 3: 3, 4: 4}, map[int]int{1: 1, 2: 2, 3: 3, 4: 4}))
	assert.Equal(t, map[int]int{1: 1, 2: 2, 3: 3, 4: 4},
		Concat(map[int]int{1: 0, 2: 0}, map[int]int{1: 1, 2: 2, 3: 3, 4: 4}))
	assert.Equal(t, map[int]int{1: 1, 2: 2, 3: 3, 4: 4},
		Concat(map[int]int{1: 1, 2: 1}, map[int]int{2: 2, 3: 3, 4: 4}))
}

func TestMap(t *testing.T) {
	assert.Equal(t,
		map[string]string{"1": "1", "2": "2"},
		Map(map[int]int{1: 1, 2: 2}, func(k, v int) (string, string) {
			return strconv.Itoa(k), strconv.Itoa(v)
		}))
	assert.Equal(t,
		map[string]string{},
		Map(map[int]int{}, func(k, v int) (string, string) {
			return strconv.Itoa(k), strconv.Itoa(v)
		}))
}

func TestValues(t *testing.T) {
	{
		keys := Values(map[int]string{1: "1", 2: "2", 3: "3", 4: "4"})
		sort.Strings(keys)
		assert.Equal(t, []string{"1", "2", "3", "4"}, keys)
	}
	assert.Equal(t, []string{}, Values(map[int]string{}))
	assert.Equal(t, []string{}, Values[int, string](nil))
}

func TestClone(t *testing.T) {
	assert.Equal(t, map[int]int{1: 1, 2: 2}, Clone(map[int]int{1: 1, 2: 2}))
	var nilMap map[int]int
	assert.Equal(t, map[int]int{}, Clone(map[int]int{}))
	assert.NotEqual(t, (map[int]int)(nil), Clone(map[int]int{}))
	assert.Equal(t, (map[int]int)(nil), Clone(nilMap))
	assert.NotEqual(t, map[int]int{}, Clone(nilMap))

	// Test new type.
	type I2I map[int]int
	assert.Equal(t, I2I{1: 1, 2: 2}, Clone(I2I{1: 1, 2: 2}))
	assert.Equal(t, "gmap.I2I", fmt.Sprintf("%T", Clone(I2I{})))

	// Test shallow clone.
	src := map[int]*int{1: ptr(1), 2: ptr(2)}
	dst := Clone(src)
	assert.Equal(t, src, dst)
	assert.True(t, src[1] == dst[1])
	assert.True(t, src[2] == dst[2])
}

// Ptr returns a pointer to the given value.
func ptr[T any](v T) *T {
	return &v
}
