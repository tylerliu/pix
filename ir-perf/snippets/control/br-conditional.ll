%cond = icmp sgt i64 %iv, 1000
br i1 %cond, label %taken, label %not_taken
taken:
br label %merge
not_taken:
br label %merge
merge: 