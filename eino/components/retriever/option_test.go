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

package retriever

import (
	"testing"

	"github.com/smartystreets/goconvey/convey"

	"github.com/cloudwego/eino/internal/mock/components/embedding"
)

func TestOptions(t *testing.T) {
	convey.Convey("test options", t, func() {
		var (
			index          = "index"
			topK           = 2
			scoreThreshold = 4.0
			subIndex       = "sub_index"
			dslInfo        = map[string]any{"dsl": "dsl"}
			e              = &embedding.MockEmbedder{}
			defaultTopK    = 1
		)

		opts := GetCommonOptions(
			&Options{
				TopK: &defaultTopK,
			},
			WithIndex(index),
			WithTopK(topK),
			WithScoreThreshold(scoreThreshold),
			WithSubIndex(subIndex),
			WithDSLInfo(dslInfo),
			WithEmbedding(e),
		)

		convey.So(opts, convey.ShouldResemble, &Options{
			Index:          &index,
			TopK:           &topK,
			ScoreThreshold: &scoreThreshold,
			SubIndex:       &subIndex,
			DSLInfo:        dslInfo,
			Embedding:      e,
		})
	})
}
