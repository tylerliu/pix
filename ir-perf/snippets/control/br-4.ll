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
%cond3 = icmp eq i64 %iv, 2
br i1 %cond3, label %taken3, label %not_taken3
taken3:
br label %merge3
not_taken3:
br label %merge3
merge3:
%cond4 = icmp eq i64 %iv, 3
br i1 %cond4, label %taken4, label %not_taken4
taken4:
br label %merge4
not_taken4:
br label %merge4
merge4: 