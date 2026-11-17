<div align="center">

<h1>Reward-Driven Learning of Concise CAD Command Sequences from Point Clouds</h1>

<p>
  <b>Yijie Ding</b><sup>1</sup>&nbsp;&nbsp;
  <b>Haobo Jiang</b><sup>1</sup>&nbsp;&nbsp;
  <b>Yang Liu</b><sup>2</sup>&nbsp;&nbsp;
  <b>Jianmin Zheng</b><sup>1,†</sup>
</p>

<p>
  <sup>1</sup>Nanyang Technological University, Singapore&nbsp;&nbsp;&nbsp;
  <sup>2</sup>Beijing Institute of Technology, China
  <br>
  <sub><sup>†</sup>Corresponding author</sub>
</p>

<h3>Computer Graphics Forum 2026</h3>

<p>
  <img alt="Journal" src="https://img.shields.io/badge/Computer%20Graphics%20Forum-2026-1f6feb">
  <img alt="Paper" src="https://img.shields.io/badge/Paper-coming%20soon-lightgrey">
  <img alt="Code" src="https://img.shields.io/badge/Code-release%20in%20progress-orange">
</p>

<img src="assets/teaser.jpg" alt="Example models from the O-CDT dataset" width="100%">

<p><i>Example models from our large-scale parametric CAD dataset (~166K models) enriched with revolution operations and free-form Bézier sketches.</i></p>

</div>

> [!NOTE]
> 🚧 **Under construction.** We are collecting and cleaning up the code, data and checkpoints, and will release them step by step. Watch or star the repo to stay tuned!

---

## 📰 News

- **[2026-11]** 🎉 Our paper has been accepted to **Computer Graphics Forum**.
- **[2026-11]** The [Onshape CAD parser](parser/) is released.

## 📖 Overview

The same shape can usually be built by many different CAD command sequences. Models that imitate human-authored sequences inherit this procedural ambiguity, along with the redundancy that comes with it. **O-CDT** (Online CAD Decision Transformer) instead treats CAD reconstruction from point clouds as a sequential decision problem, and rewards both geometric fidelity and procedural conciseness.

- **Point-to-CAD MDP.** CAD command prediction is formulated as a Markov decision process, with progressive CAD-specific rewards for sketch coverage, geometric consistency and command regularity.
- **Online CAD Decision Transformer.** Offline imitation pretraining is followed by online refinement with entropy-bounded nucleus exploration and a return-ranked replay buffer.
- **Richer modeling vocabulary.** Revolution operations and free-form cubic Bézier curves are added alongside sketch–extrude with lines, arcs and circles.
- **Large-scale dataset.** About 166K parametric CAD models support the extended operations.

## ✅ To-Do

- [x] **Parser**: Onshape → JSON command sequences, with revolve and exact B-spline → cubic Bézier conversion
- [ ] **Dataset preprocessing scripts**: filtering, deduplication, Bézier perturbation and point cloud sampling
- [ ] **O-CDT model code**: offline pretraining and online finetuning
- [ ] **Full dataset**: ~166K models with revolve operations and Bézier sketches
- [ ] **Evaluation**: metrics and scripts for reproducing the paper's results
- [ ] **Checkpoints**: pretrained O-CDT weights

## 🚀 Getting Started

The parser is the first released component. See [`parser/README.md`](parser/README.md) for setup and usage.

> [!WARNING]
> The use of this library without prior permission from Onshape/PTC constitutes a violation of the [Terms of Use](https://www.onshape.com/en/legal/terms-of-use). Specifically,
>
> *You shall not and shall not allow a third party to: [...] Use any robot, spider, scraper or other automated means to access the Service, or use any data mining, data gathering or extraction method;*
>
> Please contact Onshape Support before using a library such as this to access documents in bulk via the Onshape API.

## 📝 Citation

If you find this work useful, please consider citing:

```bibtex
@article{ding2026ocdt,
  title   = {Reward-Driven Learning of Concise CAD Command Sequences from Point Clouds},
  author  = {Ding, Yijie and Jiang, Haobo and Liu, Yang and Zheng, Jianmin},
  journal = {Computer Graphics Forum},
  year    = {2026}
}

@inproceedings{ding2026react,
  title     = {ReACT: Reward-informed Autoregressive Decision CAD Transformer},
  author    = {Ding, Yijie and Liu, Yang and Jiang, Haobo and Zheng, Jianmin},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {40},
  number    = {5},
  pages     = {3614--3622},
  year      = {2026},
  doi       = {10.1609/aaai.v40i5.37360}
}
```

> [!TIP]
> If you want to re-implement **ReACT**, this repository is a good place to start.

## 🙏 Acknowledgements

This repo stands on the shoulders of a few giants:

- [onshape-cad-parser](https://github.com/ChrisWu1997/onshape-cad-parser) from [DeepCAD](https://github.com/ChrisWu1997/DeepCAD) is where the dream began ✨. It kicked off a whole wave of sequence-based CAD modeling, and our parser started as a fork of it.
- The [ABC dataset](https://deep-geometry.github.io/abc-dataset/) is a cliché by now, yet we're all still mining it 👀. Waiting for its successor.

Thanks to all the authors for open-sourcing their work.
