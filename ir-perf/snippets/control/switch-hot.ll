%case = urem i64 %iv, 10
switch i64 %case, label %default [i64 0, label %case0
                                  i64 1, label %case1
                                  i64 2, label %case2
                                  i64 3, label %case3]
case0: br label %merge
case1: br label %merge
case2: br label %merge
case3: br label %merge
default: br label %merge
merge: 