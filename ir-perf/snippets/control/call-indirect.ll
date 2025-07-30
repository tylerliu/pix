%func_ptr = getelementptr [4 x void ()*], [4 x void ()*]* @function_table, i64 0, i64 0
%func = load void ()*, void ()** %func_ptr
call void %func() 