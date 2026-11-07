| method           | label                            |   n_seeds |   rec_macro_f1 |   seed_sd |   ci_lo |   ci_hi |   win_macro_f1 |
|:-----------------|:---------------------------------|----------:|---------------:|----------:|--------:|--------:|---------------:|
| feat_ord         | Feature KD, order variant        |         3 |          0.452 |     0.038 |   0.308 |   0.6   |          0.407 |
| gate             | Out-of-group gate (proposed)     |         3 |          0.438 |     0.03  |   0.279 |   0.595 |          0.394 |
| ce_ord           | CE only, order variant           |         3 |          0.438 |     0.02  |   0.3   |   0.588 |          0.397 |
| ungrouped_gate   | Non-grouped cross-fitting gate   |         3 |          0.429 |     0.018 |   0.28  |   0.583 |          0.395 |
| conf_gate        | CPFD-style confidence gate       |         3 |          0.427 |     0.039 |   0.281 |   0.579 |          0.386 |
| insample_gate    | In-sample residual gate          |         3 |          0.427 |     0.004 |   0.29  |   0.564 |          0.393 |
| ce               | CE only                          |         3 |          0.424 |     0.046 |   0.274 |   0.579 |          0.377 |
| gate_ord         | Gate, order variant              |         3 |          0.422 |     0.064 |   0.301 |   0.543 |          0.385 |
| feat_curteacher  | Feature KD, current-only teacher |         3 |          0.418 |     0.031 |   0.277 |   0.561 |          0.397 |
| gate_noclassnorm | Gate, no class normalisation     |         3 |          0.413 |     0.026 |   0.273 |   0.561 |          0.371 |
| saamask          | SAAMask-style adaptation         |         3 |          0.412 |     0.006 |   0.268 |   0.56  |          0.388 |
| gate_largebridge | Gate, larger bridge              |         3 |          0.409 |     0.028 |   0.26  |   0.56  |          0.378 |
| bridge_head      | Bridge + head (control)          |         3 |          0.407 |     0.011 |   0.251 |   0.573 |          0.39  |
| shuffled_gate    | Shuffled gate                    |         3 |          0.399 |     0.028 |   0.253 |   0.545 |          0.378 |
| feat             | Feature KD (ungated)             |         3 |          0.398 |     0.057 |   0.259 |   0.54  |          0.374 |
| logit_kd         | Logit KD                         |         3 |          0.381 |     0.018 |   0.246 |   0.532 |          0.351 |