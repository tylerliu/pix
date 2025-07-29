%new_agg1 = insertvalue %struct.MyStruct %agg_val, i32 42, 0
%new_agg2 = insertvalue %struct.MyStruct %new_agg1, i64 123, 1
%new_agg3 = insertvalue %struct.MyStruct %new_agg2, double 3.14, 2
%new_agg4 = insertvalue %struct.MyStruct %new_agg3, i32 99, 0 