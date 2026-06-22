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

package schema

import (
	"testing"

	"github.com/smartystreets/goconvey/convey"
)

func TestDocument(t *testing.T) {
	convey.Convey("test document", t, func() {
		var (
			subIndexes = []string{"hello", "bye"}
			score      = 1.1
			extraInfo  = "asd"
			dslInfo    = map[string]any{"hello": true}
			vector     = []float64{1.1, 2.2}
		)

		d := &Document{
			ID:       "asd",
			Content:  "qwe",
			MetaData: nil,
		}

		d.WithSubIndexes(subIndexes).
			WithDenseVector(vector).
			WithScore(score).
			WithExtraInfo(extraInfo).
			WithDSLInfo(dslInfo)

		convey.So(d.SubIndexes(), convey.ShouldEqual, subIndexes)
		convey.So(d.Score(), convey.ShouldEqual, score)
		convey.So(d.ExtraInfo(), convey.ShouldEqual, extraInfo)
		convey.So(d.DSLInfo(), convey.ShouldEqual, dslInfo)
		convey.So(d.DenseVector(), convey.ShouldEqual, vector)
	})
}
