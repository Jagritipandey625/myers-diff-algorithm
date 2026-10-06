import sys
from array import array


# ---------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------
def read_lines(path):
    """Read a file as raw bytes and split it into a list of lines (bytes)."""
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    if lines[-1] == b"":      # the file was empty, or ended with "\n"
        lines.pop()
    return lines


# ---------------------------------------------------------------
# Myers' algorithm. Works on ANY two sequences (lists of lines,
# or strings of characters), so Part A and Part B share it.
# ---------------------------------------------------------------
def shortest_edit(a, b):
    """Return the edit script as a list of '=', '-', '+' (one per step).

    '=' : a[i] == b[j], keep.  '-' : delete a[i].  '+' : insert b[j].
    """
    n, m = len(a), len(b)
    offset = n + m + 1                 # V[k] lives at index k + offset
    v = [-1] * (2 * (n + m) + 3)       # v[k] = furthest x on diagonal k;
    v[offset + 1] = 0                  # -1 means "diagonal not reached yet"
    frontiers = []                     # frontiers[d] = copy of V after round d

    # ---- forward search: find the smallest d that reaches (n, m) ----
    d = 0
    while True:
        for k in range(-d, d + 1, 2):
            i = offset + k
            # Which neighbour diagonal got us furthest in round d - 1?
            # (The -1 entries make k = -d go down and k = d go right.)
            if v[i - 1] < v[i + 1]:
                x = v[i + 1]                   # step down  (insert b[y])
            else:
                x = v[i - 1] + 1               # step right (delete a[x])
            y = x - k
            while x < n and y < m and a[x] == b[y]:   # follow the snake
                x += 1
                y += 1
            v[i] = x
            if x >= n and y >= m:
                break
        else:
            # Round d did not reach the end: remember it, go to d + 1.
            # Slice takes diagonals -d, -d+2, ..., d  (d + 1 values).
            frontiers.append(array("i", v[offset - d: offset + d + 1: 2]))
            d += 1
            continue
        break                                  # reached (n, m) in round d

    # ---- backtrack from (n, m) to (0, 0), collecting ops in reverse ----
    ops = []
    x, y = n, m
    for dd in range(d, 0, -1):
        prev = frontiers[dd - 1]               # frontier of round dd - 1
        k = x - y
        # Same decision as in the forward search, to find where we came from.
        if k == -dd or (k != dd and prev[(k + dd - 2) // 2] < prev[(k + dd) // 2]):
            prev_k = k + 1
            op = "+"
        else:
            prev_k = k - 1
            op = "-"
        prev_x = prev[(prev_k + dd - 1) // 2]
        prev_y = prev_x - prev_k
        if op == "+":
            edit_x = prev_x                    # insert moves y only
        else:
            edit_x = prev_x + 1                # delete moves x only
        ops.extend("=" * (x - edit_x))         # the snake after the edit
        ops.append(op)
        x, y = prev_x, prev_y
    ops.extend("=" * x)                        # the snake of round 0
    ops.reverse()
    return ops


def myers_diff(a, b):
    """Same as shortest_edit, but first strips the common start and end."""
    start = 0
    while start < len(a) and start < len(b) and a[start] == b[start]:
        start += 1
    end = 0
    while (end < len(a) - start and end < len(b) - start
           and a[len(a) - 1 - end] == b[len(b) - 1 - end]):
        end += 1
    middle = shortest_edit(a[start:len(a) - end], b[start:len(b) - end])
    return ["="] * start + middle + ["="] * end


# ---------------------------------------------------------------
# Part B helpers: character ranges
# ---------------------------------------------------------------
def changed_ranges(ops):
    """From a character edit script, return (old_ranges, new_ranges) text."""
    old_pos, new_pos = [], []
    i = j = 0
    for op in ops:
        if op == "=":
            i += 1
            j += 1
        elif op == "-":
            old_pos.append(i)
            i += 1
        else:
            new_pos.append(j)
            j += 1
    return format_ranges(old_pos), format_ranges(new_pos)


def format_ranges(positions):
    """[3,4,9] -> '3-5,9-10'.  Empty list -> '.'.  Touching ranges merge."""
    if not positions:
        return "."
    ranges = []
    start = prev = positions[0]
    for p in positions[1:]:
        if p != prev + 1:
            ranges.append(f"{start}-{prev + 1}")
            start = p
        prev = p
    ranges.append(f"{start}-{prev + 1}")
    return ",".join(ranges)


def highlight_line(old_line, new_line):
    """Return the bytes of the '? old | new' line for one paired line."""
    old_text = old_line.decode("utf-8")        # str: one item per code point
    new_text = new_line.decode("utf-8")
    old_r, new_r = changed_ranges(myers_diff(old_text, new_text))
    return f"? {old_r} | {new_r}\n".encode("utf-8")


# ---------------------------------------------------------------
# Output
# ---------------------------------------------------------------
def build_output(a, b, ops, with_highlight):
    """Turn the edit script into output chunks (delete-before-insert)."""
    out = []
    dels, adds = [], []        # pending change block: lines only in A / only in B

    def flush_block():
        for line in dels:
            out.append(b"-" + line + b"\n")
        for t, line in enumerate(adds):
            out.append(b"+" + line + b"\n")
            if with_highlight and t < len(dels):       # paired by position
                out.append(highlight_line(dels[t], line))
        dels.clear()
        adds.clear()

    i = j = 0                  # i walks through a, j walks through b
    for op in ops:
        if op == "-":
            dels.append(a[i])
            i += 1
        elif op == "+":
            adds.append(b[j])
            j += 1
        else:
            flush_block()
            out.append(b" " + a[i] + b"\n")
            i += 1
            j += 1
    flush_block()              # a block can be the last thing in the file
    return out


def main(argv):
    if len(argv) != 4 or argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A B", file=sys.stderr)
        return 2
    command, path_a, path_b = argv[1], argv[2], argv[3]
    try:
        a = read_lines(path_a)
        b = read_lines(path_b)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    ops = myers_diff(a, b)
    out = build_output(a, b, ops, command == "highlight")
    sys.stdout.buffer.write(b"".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
