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

// Concat returns the unions of maps as a new map.
//
// 💡 NOTE:
//
//   - Once the key conflicts, the newer value always replace the older one ([DiscardOld]),
//   - If the result is an empty set, always return an empty map instead of nil
//
// 🚀 EXAMPLE:
//
//	m := map[int]int{1: 1, 2: 2}
//	Concat(m, nil)             ⏩ map[int]int{1: 1, 2: 2}
//	Concat(m, map[int]{3: 3})  ⏩ map[int]int{1: 1, 2: 2, 3: 3}
//	Concat(m, map[int]{2: -1}) ⏩ map[int]int{1: 1, 2: -1} // "2:2" is replaced by the newer "2:-1"
//
// 💡 AKA: Merge, Union, Combine
func Concat[K comparable, V any](ms ...map[K]V) map[K]V {
	// FastPath: no map or only one map given.
	if len(ms) == 0 {
		return make(map[K]V)
	}
	if len(ms) == 1 {
		return cloneWithoutNilCheck(ms[0])
	}

	var maxLen int
	for _, m := range ms {
		if len(m) > maxLen {
			maxLen = len(m)
		}
	}
	ret := make(map[K]V, maxLen)
	// FastPath: all maps are empty.
	if maxLen == 0 {
		return ret
	}

	// Concat all maps.
	for _, m := range ms {
		for k, v := range m {
			ret[k] = v
		}
	}
	return ret
}

// Map applies function f to each key and value of map m.
// Results of f are returned as a new map.
//
// 🚀 EXAMPLE:
//
//	f := func(k, v int) (string, string) { return strconv.Itoa(k), strconv.Itoa(v) }
//	Map(map[int]int{1: 1}, f) ⏩ map[string]string{"1": "1"}
//	Map(map[int]int{}, f)     ⏩ map[string]string{}
func Map[K1, K2 comparable, V1, V2 any](m map[K1]V1, f func(K1, V1) (K2, V2)) map[K2]V2 {
	r := make(map[K2]V2, len(m))
	for k, v := range m {
		k2, v2 := f(k, v)
		r[k2] = v2
	}
	return r
}

// Values returns the values of the map m.
//
// 🚀 EXAMPLE:
//
//	m := map[int]string{1: "1", 2: "2", 3: "3", 4: "4"}
//	Values(m) ⏩ []string{"1", "4", "2", "3"} //⚠️INDETERMINATE ORDER⚠️
//
// ⚠️  WARNING: The keys values be in an indeterminate order,
func Values[K comparable, V any](m map[K]V) []V {
	r := make([]V, 0, len(m))
	for _, v := range m {
		r = append(r, v)
	}
	return r
}

// Clone returns a shallow copy of map.
// If the given map is nil, nil is returned.
//
// 🚀 EXAMPLE:
//
//	Clone(map[int]int{1: 1, 2: 2}) ⏩ map[int]int{1: 1, 2: 2}
//	Clone(map[int]int{})           ⏩ map[int]int{}
//	Clone[int, int](nil)           ⏩ nil
//
// 💡 HINT: Both keys and values are copied using assignment (=), so this is a shallow clone.
// 💡 AKA: Copy
func Clone[K comparable, V any, M ~map[K]V](m M) M {
	if m == nil {
		return nil
	}
	return cloneWithoutNilCheck(m)
}

func cloneWithoutNilCheck[K comparable, V any, M ~map[K]V](m M) M {
	r := make(M, len(m))
	for k, v := range m {
		r[k] = v
	}
	return r
}
