%func_ptr1 = getelementptr [4 x void ()*], [4 x void ()*]* @function_table, i64 0, i64 0
%func1 = load void ()*, void ()** %func_ptr1
call void %func1()
%func_ptr2 = getelementptr [4 x void ()*], [4 x void ()*]* @function_table, i64 0, i64 1
%func2 = load void ()*, void ()** %func_ptr2
call void %func2() 