%case = urem i64 %iv, 8
switch i64 %case, label %default [i64 0, label %case0
                                  i64 1, label %case1
                                  i64 2, label %case2
                                  i64 3, label %case3
                                  i64 4, label %case4
                                  i64 5, label %case5
                                  i64 6, label %case6
                                  i64 7, label %case7]
case0: br label %merge
case1: br label %merge
case2: br label %merge
case3: br label %merge
case4: br label %merge
case5: br label %merge
case6: br label %merge
case7: br label %merge
default: br label %merge
merge: 