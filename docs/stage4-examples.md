# Демонстрации stage 4

Проверено 17 ноября 2026 года.

```bash
bash run.sh --package C --version 1.0 --repository tests/chain.json --test --max-depth 2 --reverse
```

```text
C -> B
B -> A
A -> (нет)
Обратные зависимости: B, A
```

```bash
bash run.sh --package C --version 1.0 --repository tests/chain.json --test --max-depth 1 --reverse
```

```text
C -> B
B -> (нет)
Обратные зависимости: B
```

```bash
bash run.sh --package C --version 1.0 --repository tests/chain.json --test --max-depth 0 --reverse
```

```text
C -> (нет)
Обратные зависимости: (нет)
```

```bash
bash run.sh --package A --version 1.0 --repository tests/chain.json --test --max-depth 2 --reverse
```

```text
A -> (нет)
Обратные зависимости: (нет)
```

```bash
bash run.sh --package D --version 1.0 --repository tests/diamond.json --test --max-depth 2 --reverse --filter B
```

```text
D -> C
C -> A
A -> (нет)
Обратные зависимости: C, A
```

```bash
bash run.sh --package A --version 1.0 --repository tests/cycle.json --test --max-depth 10 --reverse
```

```text
A -> C
C -> B
B -> A
Обратные зависимости: C, B
```

```bash
bash run.sh --package A --version 1.0 --repository tests/self_cycle.json --test --max-depth 10 --reverse
```

```text
A -> A
Обратные зависимости: (нет)
```

```bash
bash run.sh --package A --version 1.0 --repository tests/isolated.json --test --max-depth 10 --reverse
```

```text
A -> (нет)
Обратные зависимости: (нет)
```

## Реальный PyPI

17 ноября 2026 года отдельно проверена область requests@2.32.3.
Получены метаданные по HTTP, построен полный прямой граф, затем
его рёбра развёрнуты и выполнен тот же BFS от найденной версии idna.

```text
idna@3.20 -> requests@2.32.3
requests@2.32.3 -> (нет)
```

Это проверка в указанной области; глобальный поиск по PyPI не выполнялся.
Версии могут измениться при повторном разрешении зависимостей.
