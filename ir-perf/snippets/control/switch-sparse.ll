%case = urem i64 %iv, 100
switch i64 %case, label %default [i64 10, label %case10
                                  i64 25, label %case25
                                  i64 50, label %case50
                                  i64 75, label %case75]
case10: br label %merge
case25: br label %merge
case50: br label %merge
case75: br label %merge
default: br label %merge
merge: 