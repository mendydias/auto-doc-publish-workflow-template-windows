# Method {#sec:methods}

The pipeline resolves a document manifest against a publication profile and venue. Let the effective configuration be

```{=latex}
\begin{equation}
C = M \oplus P \oplus V,
\label{eq:resolve}
\end{equation}
```

where $M$ selects manuscript content, $P$ supplies publication rules, and $V$ describes submission requirements. The operator $\oplus$ denotes validated resolution, not arbitrary option overriding. Equation \ref{eq:resolve} summarizes this design.

\begin{table}[b]
\caption{Configuration ownership by layer.}
\label{tbl:layers}
\centering
\begin{tabular}{ll}
\toprule
Layer & Responsibility \\
\midrule
Manifest & Ordered sources and document metadata \\
Profile & Class, template, engines, and restrictions \\
Venue & Submission checks and limits \\
\bottomrule
\end{tabular}
\end{table}

Table \ref{tbl:layers} summarizes the configuration ownership.
