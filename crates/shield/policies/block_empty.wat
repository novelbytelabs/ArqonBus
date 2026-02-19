;; block_empty.wat
;; Sample policy that blocks empty payloads.
;; policy_check(ptr: i32, len: i32) -> i32
;;   Returns 0 = allow, 1 = deny

(module
  ;; Export memory for host to write payload
  (memory (export "memory") 1)

  ;; policy_check: deny if len == 0
  (func (export "policy_check") (param $ptr i32) (param $len i32) (result i32)
    ;; If length is 0, return 1 (deny)
    (if (result i32)
      (i32.eqz (local.get $len))
      (then (i32.const 1))  ;; deny empty
      (else (i32.const 0))  ;; allow non-empty
    )
  )
)
