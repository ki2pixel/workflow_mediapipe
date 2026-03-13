# Compile models[](#compile-models)

Lightning Thunder is a deep learning compiler for PyTorch. It makes PyTorch programs faster both on single accelerators or in distributed settings.

The main goal for Lightning Thunder is to allow optimizing user programs in the most extensible and expressive way possible.

NOTE: Lightning Thunder is alpha and not ready for production runs. Feel free to get involved, expect a few bumps along the way.

Given a program, Thunder can generate an optimized program that:

  - computes its forward and backward passes

  - coalesces operations into efficient fusion regions

  - dispatches computations to optimized kernels

  - distributes computations optimally across machines


To do so, Thunder ships with:

  - a JIT for acquiring Python programs targeting PyTorch and custom operations

  - a multi-level IR to represent them as a trace of a reduced op-set

  - an extensible set of transformations on the trace, such as grad, fusions, distributed \(like ddp, fsdp\), functional \(like vmap, vjp, jvp\)

  - a way to dispatch operations to an extensible collection of executors


Thunder is written entirely in Python. Even its trace is represented as valid Python at all stages of transformation. This allows unprecedented levels of introspection and extensibility.

Thunder doesn’t generate device code. It acquires and transforms user programs so that it’s possible to optimally select or generate device code using fast executors like:

  - torch.compile

  - nvFuser

  - cuDNN

  - Apex

  - PyTorch eager

  - custom kernels, including those written with


Modules and functions compiled with Thunder fully interoperate with vanilla PyTorch and support PyTorch’s autograd. Also, Thunder works alongside torch.compile to leverage its state-of-the-art optimizations.

Here is a simple example of how thunder lets you compile and run PyTorch modules and functions:

\[4, 4

,

4, 4

\]\)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 ` ` import torch import thunder def foo(a, b): return a + b jitted_foo = thunder.jit(foo) a = torch.full((2, 2), 1) b = torch.full((2, 2), 3) result = jitted_foo(a, b) print(result) # prints # tensor(`

The compiled function ` jitted_foo ` takes and returns PyTorch tensors, just like the original function, so modules and functions compiled by Thunder can be used as part of bigger PyTorch programs.

