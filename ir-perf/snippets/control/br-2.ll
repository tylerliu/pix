%cond1 = icmp eq i64 %iv, 0
br i1 %cond1, label %taken1, label %not_taken1
taken1:
br label %merge1
not_taken1:
br label %merge1
merge1:
%cond2 = icmp eq i64 %iv, 1
br i1 %cond2, label %taken2, label %not_taken2
taken2:
br label %merge2
not_taken2:
br label %merge2
merge2: 