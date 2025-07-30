%cond = icmp eq i64 %iv, 0
br i1 %cond, label %taken, label %not_taken
taken:
br label %merge
not_taken:
br label %merge
merge: 