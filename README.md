# kubism

Open an ssh proxy to a kube API and build its relevant kubeconfig.

Requires `kubectl` (but i guess you have it).

## install

In some virtual environment:

```bash
pip install -e .
```

## usage

```bash
kubism hostname # without the zone

# [ctrl+C to stop]
```

## backgrounding scenario

If you don't want to open another term:

```bash
kubism hostname
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
