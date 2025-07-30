%cond = icmp eq i64 %iv, 0
br i1 %cond, label %not_taken, label %taken
not_taken:
taken: 