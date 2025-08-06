; Adjust the DataLayout and Triple for your target, or let llc infer them.
; (You can `llc -march=... -o-` to see the defaults.)

; Declare an external "sink" so the compiler can't optimize away your result.
declare void @sink(i64)

; Single large array for all memory access patterns
; Size: 67,108,864 entries (512MB) - largest size needed
@buf = private local_unnamed_addr global [67108864 x i64] zeroinitializer, align 64 ; 512MB

define void @bench_loop(i64 %N) {
entry:
  br label %loop

loop:
  %iv    = phi i64 [0, %entry], [%next_iv, %loop]
  %sum   = phi i64 [0, %entry], [%next_sum, %loop]

  ; --- The instruction you want to measure: ---
  ; Snippet will use @buf with different access patterns:
  ; - Small indices (0-255) for L1 cache hits
  ; - Medium indices (0-4095) for L2 cache hits  
  ; - Large indices (0-65535) for L3 cache hits
  ; - Full range (0-67108863) for cache misses
  ; Use %increment1, %increment2, etc. for different pointer calculations
  ; -------------------------------------------

  ; increment loop counter
  %next_iv   = add  i64 %iv, 1
  %cmp   = icmp slt  i64 %iv, %N
  br     i1 %cmp, label %loop, label %exit

exit:
  call void @sink(i64 %sum)    ; prevent dead-code elimination
  ret void
} 