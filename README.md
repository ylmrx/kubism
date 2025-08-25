# kubism

Open an ssh proxy to a kube API and build its relevant kubeconfig.

There's no error control at all (yet) (ie. ugly output on connection issues, and
killed terminal doesn't clear the tmp folder)

## install

In some virtual environment:

```bash
pip install -e .
```

## usage

```bash
kubism hostname # without the zone

# open a subshell (run $SHELL) with the $KUBECONFIG set...

# [ctrl+D to exit]
# clear the crypto, and close the tunnel
```

You can have the tunnel sticking to foreground using the `--foreground` flag. Use
`Ctrl+C` to close it.

## backgrounding scenario

If you don't want to open another term:

```bash
kubism -f hostname
# [Ctrl+Z] <- suspends process in the background
bg %1 # <- continue it

# copy/paste the `export KUBECONFIG=...` line
# Do your thing as the proxy works
```

## host picker

Requires: https://github.com/charmbracelet/gum

```bash
# in your bashrc/zshrc/...
function proxykube {
  __cp=$(tailscale status --json | \
    jq -r '[.Peer | map(select( has("Tags"))) | keys[] as $k
      | "\(.[$k].DNSName[:-1]) \(.[$k].Tags )"
      | select(test("^kube-(master|controlplane)"))] | sort[]' | \
    gum filter --no-fuzzy | cut -f 1 -d ' ')
  /path/to/venv/bin/kubism $__cp
}
```
