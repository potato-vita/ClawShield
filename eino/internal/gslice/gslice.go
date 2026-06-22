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

// ToMap collects elements of slice to map, both map keys and values are produced
// by mapping function f.
//
// 🚀 EXAMPLE:
//
//	type Foo struct {
//		ID   int
//		Name string
//	}
//	mapper := func(f Foo) (int, string) { return f.ID, f.Name }
//	ToMap([]Foo{}, mapper) ⏩ map[int]string{}
//	s := []Foo{{1, "one"}, {2, "two"}, {3, "three"}}
//	ToMap(s, mapper)       ⏩ map[int]string{1: "one", 2: "two", 3: "three"}
func ToMap[T, V any, K comparable](s []T, f func(T) (K, V)) map[K]V {
	m := make(map[K]V, len(s))
	for _, e := range s {
		k, v := f(e)
		m[k] = v
	}
	return m
}
