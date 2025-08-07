# kubism

Open an ssh proxy to a kube API and build its relevant kubeconfig

## usage

```bash
python main.py hostname

[ctrl+C to stop]
```

## backgrounding scenario

If you don't want to open another term:

```bash
python main.py hostname
# [Ctrl+Z] <- suspends process in the background
bg %1 # <- continue it

# Do your thing as the proxy works
```
