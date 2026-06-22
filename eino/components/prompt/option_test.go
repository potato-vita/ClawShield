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

package prompt

import (
	"testing"

	"github.com/smartystreets/goconvey/convey"
)

type implOption struct {
	userID int64
	name   string
}

func WithUserID(uid int64) Option {
	return WrapImplSpecificOptFn[implOption](func(i *implOption) {
		i.userID = uid
	})
}

func WithName(n string) Option {
	return WrapImplSpecificOptFn[implOption](func(i *implOption) {
		i.name = n
	})
}

func TestImplSpecificOption(t *testing.T) {
	convey.Convey("impl_specific_option", t, func() {
		opt := GetImplSpecificOptions(&implOption{}, WithUserID(101), WithName("Wang"))

		convey.So(opt, convey.ShouldEqual, &implOption{
			userID: 101,
			name:   "Wang",
		})
	})
}
