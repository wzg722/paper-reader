/* ============================================================
   PaperMind 研读 — 原型演示数据（内存模拟，无后端）
   ⚠ 论文元信息基于真实论文（引用数为演示近似值）
   ============================================================ */
window.PM = {

/* ---------- 论文库（7 篇真实论文，CV/OCR/NLP 方向） ---------- */
papers: [
  {
    id:0, title:"Attention Is All You Need",
    titleZh:"注意力就是你所需要的一切",
    intro:"提出纯注意力架构 Transformer，抛弃循环与卷积，奠定现代大模型与多模态的基础。",
    authors:"Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, ...",
    venue:"NeurIPS 2017", year:2017, doi:"10.48550/arXiv.1706.03762",
    link:"https://arxiv.org/abs/1706.03762",
    cites:128000, read:100, status:"在读", cat:"神经网络", starred:true, tags:["Transformer","NLP","深度学习"],
    abs:"We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
    absZh:"我们提出一种全新的简单网络架构——Transformer，完全基于注意力机制，彻底摒弃了循环与卷积结构。在两个机器翻译任务上的实验表明，该模型在质量上更优，同时并行性更好，训练时间大幅缩短。",
    summary:{
      core:"用纯注意力机制取代循环/卷积，实现并行化、可训练的长程依赖建模。",
      problem:"RNN 序列建模无法并行、长距离依赖易丢失，训练成本高。",
      method:["多头自注意力（Multi-Head Self-Attention）并行捕捉多角度依赖","位置编码（Positional Encoding）注入序列顺序信息","残差连接 + LayerNorm + 逐位置前馈网络构成编码-解码栈","自回归解码 + 掩码注意力保证未来信息不可见"],
      result:"WMT 英德 28.4 BLEU（当时 SOTA，领先集成模型 2 BLEU）；训练成本仅为最优模型 1/7。",
      limit:"自注意力对超长序列为 O(n²) 复杂度；论文未解决超长文本高效化问题。"
    },
    glossary:[["attention mechanism","注意力机制","按相关性加权聚合信息"],["self-attention","自注意力","序列内部元素两两交互"],["positional encoding","位置编码","注入词序信息"],["parallelization","并行化","摆脱串行计算的限制"],["BLEU","双语评估替补","机器翻译自动评价指标"]]
  },
  {
    id:1, title:"Deep Residual Learning for Image Recognition",
    titleZh:"用于图像识别的深度残差学习",
    intro:"残差连接解决深层网络退化问题，152 层深度拿下 ILSVRC 2015 冠军，深度学习基石之一。",
    authors:"Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun",
    venue:"CVPR 2016", year:2016, doi:"10.1109/CVPR.2016.90",
    link:"https://arxiv.org/abs/1512.03385",
    cites:210000, read:100, status:"读完", cat:"图像分类", starred:true, tags:["ResNet","图像分类","CV"],
    abs:"Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. On the ImageNet dataset we evaluate residual nets with a depth of up to 152 layers—8x deeper than VGG nets but still having lower complexity. An ensemble of these residual nets achieves 3.57% error on the ImageNet test set.",
    absZh:"更深的神经网络更难训练。我们提出残差学习框架，让网络能训练到远超以往的深度。在 ImageNet 上评估了深达 152 层的残差网络——比 VGG 深 8 倍但复杂度更低。集成后的残差网络在 ImageNet 测试集上取得 3.57% 的误差。",
    summary:{
      core:"通过残差连接（恒等捷径）解决深层网络退化问题，训练出 152 层深度网络。",
      problem:"网络越深，优化越难，出现『退化』——更深反而误差更高。",
      method:["引入恒等捷径连接：F(x)+x，使网络只需学习残差","瓶颈结构（Bottleneck）降低计算量","批归一化 + 残差组合支撑千层网络","VGG 之后首次证明深度是性能关键"],
      result:"ILSVRC 2015 冠军，top-5 误差 3.57%，超过人类水平（5.1%）。",
      limit:"残差网络理论解释（为什么有效）当时未完全清楚；超深网络仍有训练稳定性问题。"
    },
    glossary:[["residual learning","残差学习","学习目标从 F(x) 变为 F(x)+x"],["degradation","退化问题","深层网络训练误差反而更高"],["shortcut connection","捷径连接","跨层恒等映射"],["bottleneck","瓶颈模块","1x1 降维-卷积-升维"]]
  },
  {
    id:2, title:"An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
    titleZh:"一张图等于 16x16 个词：规模化图像识别 Transformer",
    intro:"把图像切成 16x16 块当『词』输入 Transformer，大数据预训练后超越 CNN，视觉大模型开山之作。",
    authors:"Alexey Dosovitskiy, Lucas Beyer, Alexander Kolesnikov, ...",
    venue:"ICLR 2021", year:2021, doi:"10.48550/arXiv.2010.11929",
    link:"https://arxiv.org/abs/2010.11929",
    cites:98000, read:45, status:"在读", cat:"图像分类", starred:false, tags:["ViT","Transformer","CV"],
    abs:"While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. We show that reliance on CNNs is not necessary and a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks.",
    absZh:"Transformer 已成为 NLP 的事实标准，但在计算机视觉中的应用仍然有限。我们证明：对 CNN 的依赖并非必要，直接将纯 Transformer 应用于图像块序列，就能在图像分类任务上表现非常好。",
    summary:{
      core:"将图像切成 16x16 的块（patch）当作『词』，直接用纯 Transformer 做图像分类。",
      problem:"CNN 归纳偏置（局部性/平移不变）是否是视觉理解所必需？",
      method:["图像分块 + 线性投影成 patch embedding","可学习的类别标记（[CLS] token）聚合全局信息","预训练规模是关键：中小数据集上不如 CNN，大数据集上超越","位置嵌入保留空间结构"],
      result:"ViT-L/16 在 ImageNet 达到 88.55% top-1（无卷积、预训练于 JFT-300M）。",
      limit:"需要海量预训练数据；平移/尺度不变性依赖数据增强。"
    },
    glossary:[["patch embedding","图像块嵌入","将图像块线性投影为向量"],["inductive bias","归纳偏置","模型先验（如 CNN 的局部性）"],["CLS token","类别标记","聚合整图信息的特殊 token"],["fine-tuning","微调","在预训练基础上用小数据调整"]]
  },
  {
    id:3, title:"End-to-End Object Detection with Transformers",
    titleZh:"基于 Transformer 的端到端目标检测",
    intro:"把检测当集合预测，用 Transformer+二分匹配端到端输出目标框，干掉锚框与 NMS。",
    authors:"Nicolas Carion, Francisco Massa, Gabriel Synnaeve, ...",
    venue:"ECCV 2020", year:2020, doi:"10.1007/978-3-030-58452-8_13",
    link:"https://arxiv.org/abs/2005.12872",
    cites:42000, read:10, status:"想读", cat:"目标检测", starred:false, tags:["DETR","目标检测","Transformer"],
    abs:"We present a new method that views object detection as a direct set prediction problem. Our approach streamlines the detection pipeline, effectively removing the need for many hand-designed components like a non-maximum suppression procedure or anchor generation that explicitly encode our prior knowledge about the task.",
    absZh:"我们提出一种新方法，将目标检测视为直接的集合预测问题。该方法精简了检测流程，去除了 NMS（非极大值抑制）和锚框生成等大量手工设计组件。",
    summary:{
      core:"把检测视为『集合预测』，用 Transformer + 二分图匹配一步到位输出目标框。",
      problem:"传统检测依赖锚框、NMS 等手工组件，流程复杂且难以端到端优化。",
      method:["可学习的 object queries 查询序列","匈牙利算法做预测与真值的二分匹配","去除 NMS 与锚框设计"],
      result:"COCO 上 ResNet-50 达到 42 AP，与大而深的 Faster R-CNN 基线相当，但更简洁。",
      limit:"小目标检测弱；训练收敛慢（500 epochs）。"
    },
    glossary:[["set prediction","集合预测","把输出视为无序集合"],["NMS","非极大值抑制","传统检测的冗余框过滤"],["bipartite matching","二分图匹配","预测与真值一一对应"],["object queries","目标查询","可学习的检测槽位"]]
  },
  {
    id:4, title:"PP-OCR: A Practical Ultra Lightweight OCR System",
    titleZh:"PP-OCR：一个实用的超轻量 OCR 系统",
    intro:"超轻量三段式 OCR（检测+方向分类+识别），模型仅 3.5M，CPU 实时运行，团队正在使用的方案。",
    authors:"Yuning Du, Chenxia Li, Ruoyu Guo, ...",
    venue:"arXiv 2020", year:2020, doi:"10.48550/arXiv.2009.09941",
    link:"https://arxiv.org/abs/2009.09941",
    cites:7200, read:80, status:"在读", cat:"OCR", starred:true, tags:["OCR","PP-OCR","实用系统"],
    abs:"The main contributions are as follows: (1) We propose a practical ultra lightweight OCR system, i.e., PP-OCR, which is composed of text detection, text recognition and text angle classification modules. (2) We propose a unified strategy to construct a more effective and compact model for each module. The models are trained on real data and pseudo data, and the whole system can achieve 3.5M model size.",
    absZh:"主要贡献如下：(1) 提出实用超轻量 OCR 系统 PP-OCR，由文本检测、文本识别和文本方向分类三大模块组成；(2) 提出统一策略为每个模块构建更有效、更紧凑的模型。模型在真实数据和伪数据上训练，整个系统模型大小仅 3.5M。",
    summary:{
      core:"面向真实场景的端到端轻量 OCR 系统：检测 + 方向分类 + 识别三段式。",
      problem:"学术界 OCR 方案精度高但模型重、部署难；业界需要移动端可用的轻量方案。",
      method:["DB（可微分二值化）文本检测 + 轻量骨干 MobileNetV3","方向分类器解决 90/180 度倒置文本","CRNN/SVTR 序列识别 + CTC 解码","真实数据 + 伪数据（合成）联合训练","蒸馏、剪枝、量化进一步压缩"],
      result:"模型总大小 3.5M，中英文识别精度与大规模模型相当，CPU 实时运行。",
      limit:"复杂版面（表格/公式/多栏）支持有限，后续由 PP-StructureV3 补足。"
    },
    glossary:[["text detection","文本检测","定位文本所在区域"],["text recognition","文本识别","将文本行转为字符序列"],["DB","可微分二值化","基于分割的可学习阈值检测"],["distillation","知识蒸馏","大模型教小模型"]]
  },
  {
    id:5, title:"TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models",
    titleZh:"TrOCR：基于预训练 Transformer 的光学字符识别",
    intro:"ViT 编码+RoBERTa 解码的双 Transformer OCR，吃大规模预训练红利，手写与印刷文本双强。",
    authors:"Minghao Li, Tengchao Lv, Jingye Chen, ...",
    venue:"arXiv 2021", year:2021, doi:"10.48550/arXiv.2109.10282",
    link:"https://arxiv.org/abs/2109.10282",
    cites:3900, read:0, status:"想读", cat:"OCR", starred:false, tags:["TrOCR","OCR","Transformer"],
    abs:"Text recognition is a long-standing research topic for computer vision. In this work, we propose an end-to-end text recognition approach with pre-trained image Transformer and text Transformer models (TrOCR), which utilize the pre-trained models on large-scale data to initialize the visual and linguistic components.",
    absZh:"文本识别是计算机视觉中长期存在的研究课题。本文提出端到端文本识别方法 TrOCR，使用在大规模数据上预训练的图像 Transformer 与文本 Transformer 模型，分别初始化视觉与语言组件。",
    summary:{
      core:"OCR 识别用『图像编码器 + 文本解码器』双 Transformer，继承大规模预训练红利。",
      problem:"传统 CRNN 需要大量标注数据，泛化与手写场景表现有限。",
      method:["ViT/DeiT 做视觉编码器，RoBERTa 做语言解码器","预训练（合成数据 + 真实数据）→ 下游微调两阶段","无 CNN，端到端序列生成"],
      result:"手写文本（IAM）与印刷文本（SROIE）基准上超越当时 SOTA 方法。",
      limit:"训练依赖海量数据；模型参数量较大，轻量化需后续工作。"
    },
    glossary:[["encoder-decoder","编码器-解码器","视觉→语言的序列生成结构"],["pre-training","预训练","大数据先学通用表征"],["fine-tuning","微调","小数据适配任务"]]
  },
  {
    id:6, title:"MASTER: Multi-Aspect Non-local Network for Scene Text Recognition",
    titleZh:"MASTER：多角度非局部网络用于场景文本识别",
    intro:"多角度编码器+Transformer 解码器，捕捉全局上下文，提升不规则场景文本识别精度。",
    authors:"Ning Lu, Wenwen Yu, Xianbiao Qi, ...",
    venue:"Pattern Recognition 2021", year:2021, doi:"10.1016/j.patcog.2021.108065",
    link:"https://arxiv.org/abs/1910.02562",
    cites:1500, read:0, status:"想读", cat:"OCR", starred:false, tags:["MASTER","STR","CV"],
    abs:"Scene text recognition has been a hot research topic in computer vision. In this paper, we propose a novel architecture, called MASTER, to exploit the global context information in scene text recognition. The MASTER is composed of a Multi-Aspect Encoder and a Transformer Decoder.",
    absZh:"场景文本识别一直是计算机视觉的热点课题。本文提出名为 MASTER 的新架构，利用全局上下文信息进行场景文本识别。MASTER 由多角度编码器和 Transformer 解码器组成。",
    summary:{
      core:"多角度全局编码 + Transformer 解码，提升不规则场景文本识别。",
      problem:"RNN/注意力局部建模难以捕捉文本行全局与多维上下文。",
      method:["多角度编码器：并行捕捉多个注意力子空间","Transformer 解码器直接生成字符序列","简化训练流程，无需额外修正模块"],
      result:"多个 STR 基准（IIIT5K、SVT、ICDAR 系列）达到当时 SOTA。",
      limit:"依赖大数据训练；对弯曲文本的几何建模仍有限。"
    },
    glossary:[["scene text recognition","场景文本识别","自然场景中的文字识别"],["non-local","非局部","直接建模长距离依赖"],["aspect","角度/方面","多视角注意力子空间"]]
  }
],

/* ---------- 阅读器演示正文：Attention Is All You Need 节选（公开原文 + 逐段译文） ---------- */
readerPaper: {
  title:"Attention Is All You Need",
  outline:[
    {id:"s1", zh:"摘要"},
    {id:"s2", zh:"1 引言"},
    {id:"s3", zh:"2 背景"},
    {id:"s4", zh:"3 模型架构"},
    {id:"s5", zh:"4 实验"},
    {id:"s6", zh:"5 结论"}
  ],
  blocks:[
    {sec:"s1", type:"abstract", en:"We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
     zh:"我们提出一种全新的简单网络架构——Transformer，完全基于注意力机制，彻底摒弃了循环与卷积结构。在两个机器翻译任务上的实验表明：这类模型质量更优、并行性更好，且训练时间大幅缩短。"},
    {sec:"s1", type:"meta", en:"Vaswani et al. NeurIPS 2017", zh:"Vaswani 等人 NeurIPS 2017"},
    {sec:"s2", type:"p", en:"Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular, have been firmly established as state of the art approaches in sequence modeling and transduction problems such as language modeling and machine translation. Numerous efforts have since continued to push the boundaries of recurrent language models and encoder-decoder architectures.",
     zh:"循环神经网络，尤其是长短时记忆网络（LSTM）和门控循环网络（GRU），在序列建模与序列转换问题（如语言建模、机器翻译）中一直是公认的最先进方法。此后大量研究不断推动循环语言模型与编码器-解码器架构的边界。"},
    {sec:"s2", type:"p", en:"Recurrent models typically factor computation along the symbol positions of the input and output sequences. Aligning the positions to steps in computation time, they generate a sequence of hidden states ht, as a function of the previous hidden state ht−1 and the input for position t. This inherently sequential nature precludes parallelization within training examples, which becomes critical at longer sequence lengths.",
     zh:"循环模型通常沿输入/输出序列的符号位置分解计算，将位置与计算时间步对齐，按 h_t = f(h_{t−1}, x_t) 生成隐状态序列。这种固有的串行特性使得训练样本内部无法并行化，而序列越长，这一问题越致命。"},
    {sec:"s2", type:"p", en:"Attention mechanisms have become an integral part of compelling sequence modeling and transduction models in various tasks, allowing modeling of dependencies without regard to their distance in the input or output sequences. In all but a few cases, however, such attention mechanisms are used in conjunction with a recurrent network.",
     zh:"注意力机制已成为各类序列建模与转换模型不可或缺的组成部分，它允许建模任意距离的依赖关系。然而在绝大多数情况下，注意力机制仍与循环网络搭配使用。"},
    {sec:"s2", type:"p", en:"In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for significantly more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours on eight P100 GPUs.",
     zh:"本文提出 Transformer 架构：摒弃循环结构，完全依赖注意力机制捕获输入输出之间的全局依赖。Transformer 支持显著更高的并行度，在 8 块 P100 GPU 上仅训练 12 小时即可达到新的翻译质量 SOTA。"},
    {sec:"s3", type:"p", en:"The goal of reducing sequential computation also forms the foundation of the Extended Neural GPU, ByteNet and ConvS2S, all of which use convolutional neural networks as basic building block, computing hidden representations in parallel for all input and output positions. In these models, the number of operations required to relate signals from two arbitrary input or output positions grows in the distance between positions.",
     zh:"减少串行计算的目标同样构成了 Extended Neural GPU、ByteNet 和 ConvS2S 的基础——它们都用卷积神经网络作为基本构件，对所有输入/输出位置并行计算隐表示。但这类模型中，关联两个任意位置信号所需的操作数会随位置间距线性增长。"},
    {sec:"s3", type:"p", en:"Self-attention, sometimes called intra-attention, is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. Self-attention has been used successfully in a variety of tasks including reading comprehension, abstractive summarization, textual entailment and learning task-independent sentence representations.",
     zh:"自注意力（Self-attention），有时也称内部注意力，是关联单个序列内部不同位置以计算序列表示的注意力机制。自注意力已在阅读理解、生成式摘要、文本蕴含以及学习任务无关的句子表示等任务中成功应用。"},
    {sec:"s4", type:"p", en:"An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key.",
     zh:"注意力函数可描述为：将查询（Query）和一组键值对（Key-Value）映射为输出，其中查询、键、值、输出均为向量。输出是值的加权和，每个值的权重由查询与对应键的兼容性函数计算得出。"},
    {sec:"s4", type:"p", en:"Instead of performing a single attention function, we found it beneficial to linearly project the queries, keys and values h times with different, learned linear projections to dk, dk and dv dimensions, respectively. On each of these projected versions of queries, keys and values we then perform the attention function in parallel, yielding dv-dimensional output values. These are concatenated and once again projected, resulting in the final values.",
     zh:"我们发现，与其执行单个注意力函数，不如将查询、键、值分别用 h 组不同的可学习线性投影映射到 d_k、d_k、d_v 维，并行执行注意力后再拼接并投影，效果更佳——这就是多头注意力（Multi-Head Attention）。"},
    {sec:"s5", type:"p", en:"The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the best existing results including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, the Transformer establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs.",
     zh:"在 WMT 2014 英德翻译任务上，Transformer 取得 28.4 BLEU，比包含集成模型在内的最佳结果高出 2 BLEU 以上。在 WMT 2014 英法任务上，单模型在 8 块 GPU 上训练 3.5 天即创下 41.8 BLEU 的新纪录。"},
    {sec:"s5", type:"p", en:"The Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. Even in the base model, dropping the attention layer makes performance drop to 27.5 BLEU due to overfitting.",
     zh:"Transformer 是第一个完全依赖自注意力计算输入输出表示、不借助序列对齐的 RNN 或卷积的序列转换模型。即使仅移除基础模型中的注意力层，性能也会因过拟合跌至 27.5 BLEU。"},
    {sec:"s6", type:"p", en:"In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention. We believe this work marks a step towards a more general and natural kind of machine learning that operates on sets and interactions between them.",
     zh:"本文提出 Transformer——第一个完全基于注意力的序列转换模型，用多头自注意力取代了编码器-解码器架构中最常用的循环层。我们相信，这项工作标志着向更通用、更自然的机器学习迈出一步：直接对集合及其相互关系进行运算。"}
  ],

  /* 划词翻译词典（演示用，命中即显示译文） */
  hoverDict:{
    "recurrent neural networks":"循环神经网络（RNN）",
    "long short-term memory":"长短时记忆网络（LSTM）",
    "attention mechanism":"注意力机制：按相关性加权聚合信息的机制",
    "self-attention":"自注意力：序列内部位置两两交互",
    "parallelization":"并行化：多个计算同时进行",
    "sequence modeling":"序列建模",
    "machine translation":"机器翻译",
    "encoder-decoder":"编码器-解码器架构",
    "hidden states":"隐状态",
    "overfitting":"过拟合：在训练集上过度拟合",
    "transduction":"序列转换（输入输出均为序列）",
    "compatibility function":"兼容性函数：衡量查询与键的匹配程度"
  }
},

/* ---------- AI 对话演示回答 ---------- */
aiReplies:{
  "这篇论文的核心创新是什么？":"核心创新是**完全摒弃循环与卷积**，仅用注意力机制建模序列：① 多头自注意力并行捕捉多角度依赖；② 位置编码注入顺序信息；③ 整栈残差 + LayerNorm 支撑超深训练。这是第一个纯注意力的序列转换模型。",
  "论文解决了什么问题？":"解决 RNN 两大痛点：**无法并行**（串行计算导致训练慢）与**长距离依赖丢失**（信息随距离衰减）。Transformer 让任意两位置直接相连，训练时间降到最优 RNN 模型的 1/7。",
  "实验结果如何？":"WMT14 英德 28.4 BLEU（超过含集成在内的最佳结果 2+ BLEU）；英法 41.8 BLEU（单模型新纪录）；8×P100 训练仅 12 小时。消融实验显示移除注意力层后跌至 27.5 BLEU，证明注意力是核心。",
  "有什么局限性？":"自注意力对超长序列是 O(n²) 复杂度，论文未处理超长文本高效化（后续被 Longformer、稀疏注意力等解决）；另外当时未证明可扩展到视觉/多模态（ViT、DETR 是后续工作）。",
  "对我的 OCR 项目有什么启发？":"① 序列建模范式可直接迁移：TrOCR 用 Transformer 替换 CRNN 即是例证；② 预训练-微调两阶段策略对标注数据不足的 OCR 场景很关键；③ 注意力可视化可辅助定位识别错误（如漏字、错序）。"
},

/* ---------- 图表占位说明 ---------- */
figures:["图1：Transformer 整体架构（编码-解码栈）","图2：多头注意力计算流程（Q/K/V 投影）","图3：位置编码可视化（正弦波叠加）"],

/* ---------- 相关论文 ---------- */
related:[["BERT: Pre-training of Deep Bidirectional Transformers",2],["GPT: Improving Language Understanding by Generative Pre-Training",2],["Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context",0],["Longformer: The Long-Document Transformer",0]],

/* ---------- 网页浏览导入：外部来源站点（预置 builtin + 用户自定义 custom） ----------
   type: builtin=预置（不可删除） custom=用户添加（可删除，存 localStorage）
   mock: 演示数据（真实产品走后端站点适配器抓取） */
browseSources: [
  {name:"arXiv", icon:"🅰", type:"builtin", resolved:true, url:"arxiv.org", desc:"预印本（物理/数学/CS 全领域）", mock:[
    {id:"2608.10684v1", title:"Embedding Rotation Invariance for Provable Multi-Oriented Scene Text Recognition", authors:"Zhibin Ma, Pengwen Dai…", date:"2026-08-11", venue:"arXiv 2026"},
    {id:"2608.03884v1", title:"BanglaWild: An In-the-Wild Bengali Scene Text Recognition Benchmark for OCR and Vision-Language Models", authors:"Sadab Shiper, Tawsif Tashwar Dipto…", date:"2026-08-04", venue:"arXiv 2026"},
    {id:"2607.23194v1", title:"Out-of-Length Scene Text Recognition: A Two-Axis Diagnosis and a Training-Free Fix", authors:"Zobeir Raisi, John Zelek…", date:"2026-07-25", venue:"arXiv 2026"},
    {id:"2607.13458v1", title:"2D Rotary Position Embedding for Scene Text Recognition with Transformers", authors:"Zobeir Raisi…", date:"2026-07-15", venue:"arXiv 2026"},
    {id:"2606.24484v1", title:"Advancing WordArt-Oriented Scene Text Recognition: Datasets and Methods", authors:"Xingsong Ye, Yongkun Du…", date:"2026-06-23", venue:"arXiv 2026"},
    {id:"2605.14885v1", title:"Masked Next-Scale Prediction for Self-supervised Scene Text Recognition", authors:"Zhuohao Chen, Zeng Li…", date:"2026-05-14", venue:"arXiv 2026"},
    {id:"2604.23685v1", title:"Reading in the Dark: Low-light Scene Text Recognition", authors:"Xuanshuo Fu, Lei Kang…", date:"2026-04-26", venue:"arXiv 2026"},
    {id:"2603.13886v1", title:"Multi-Modal Character Localization and Extraction for Chinese Text Recognition", authors:"Qilong Li, Chongsheng Zhang…", date:"2026-03-14", venue:"arXiv 2026"},
    {id:"2603.03580v1", title:"An Effective Data Augmentation Method by Asking Questions about Scene Text Images", authors:"Xu Yao, Lei Kang…", date:"2026-03-03", venue:"arXiv 2026"},
    {id:"2602.06450v2", title:"What Is Wrong with Synthetic Data for Scene Text Recognition? A Strong Synthetic Engine with Diverse Simulations and Self-Evolution", authors:"Xingsong Ye, Yongkun Du…", date:"2026-02-06", venue:"arXiv 2026"},
    {id:"2512.01422v1", title:"MDiff4STR: Mask Diffusion Model for Scene Text Recognition", authors:"Yongkun Du, Miaomiao Zhao…", date:"2025-12-01", venue:"arXiv 2025"},
    {id:"2511.23071v2", title:"Bharat Scene Text: A Novel Comprehensive Dataset and Benchmark for Indian Language Scene Text Understanding", authors:"Anik De, Abhirama Subramanyam Penamakuri…", date:"2025-11-28", venue:"arXiv 2025"},
    {id:"2511.19820v2", title:"CropVLM: Learning to Zoom for Fine-Grained Vision-Language Perception", authors:"Miguel Carvalho, Helder Dias…", date:"2025-11-25", venue:"arXiv 2025"},
    {id:"2511.08133v1", title:"OTSNet: A Neurocognitive-Inspired Observation-Thinking-Spelling Pipeline for Scene Text Recognition", authors:"Lixu Sun, Nurmemet Yolwas…", date:"2025-11-11", venue:"arXiv 2025"},
    {id:"2510.01651v1", title:"LadderMoE: Ladder-Side Mixture of Experts Adapters for Bronze Inscription Recognition", authors:"Rixin Zhou, Peiqiang Qiu…", date:"2025-10-02", venue:"arXiv 2025"},
    {id:"2508.01153v1", title:"TEACH: Text Encoding as Curriculum Hints for Scene Text Recognition", authors:"Xiahan Yang, Hui Zheng…", date:"2025-08-02", venue:"arXiv 2025"},
    {id:"2507.02200v1", title:"ESTR-CoT: Towards Explainable and Accurate Event Stream based Scene Text Recognition with Chain-of-Thought Reasoning", authors:"Xiao Wang, Jingtao Jiang…", date:"2025-07-02", venue:"arXiv 2025"},
    {id:"2503.18883v1", title:"Efficient and Accurate Scene Text Recognition with Cascaded-Transformers", authors:"Savas Ozkan, Andrea Maracani…", date:"2025-03-24", venue:"arXiv 2025"},
    {id:"2503.18746v1", title:"Linguistics-aware Masked Image Modeling for Self-supervised Scene Text Recognition", authors:"Yifei Zhang, Chang Liu…", date:"2025-03-24", venue:"arXiv 2025"},
    {id:"2503.16184v1", title:"Accurate Scene Text Recognition with Efficient Model Scaling and Cloze Self-Distillation", authors:"Andrea Maracani, Savas Ozkan…", date:"2025-03-20", venue:"arXiv 2025"},
    {id:"2503.15639v2", title:"A Lightweight Context-Driven Training-Free Network for Scene Text Segmentation and Recognition", authors:"Ritabrata Chakraborty, Shivakumara Palaiahnakote…", date:"2025-03-19", venue:"arXiv 2025"},
    {id:"2502.09026v1", title:"Billet Number Recognition Based on Test-Time Adaptation", authors:"Yuan Wei, Xiuzhuang Zhou…", date:"2025-02-13", venue:"arXiv 2025"},
    {id:"2502.09020v1", title:"EventSTR: A Benchmark Dataset and Baselines for Event Stream based Scene Text Recognition", authors:"Xiao Wang, Jingtao Jiang…", date:"2025-02-13", venue:"arXiv 2025"},
    {id:"2501.15558v1", title:"Ocean-OCR: Towards General OCR Application via a Vision-Language Model", authors:"Song Chen, Xinyu Guo…", date:"2025-01-26", venue:"arXiv 2025"},
    {id:"2412.10159v1", title:"Arbitrary Reading Order Scene Text Spotter with Local Semantics Guidance", authors:"Jiahao Lyu, Wei Wang…", date:"2024-12-13", venue:"arXiv 2024"},
    {id:"2412.01137v2", title:"TextSSR: Diffusion-based Data Synthesis for Scene Text Recognition", authors:"Xingsong Ye, Yongkun Du…", date:"2024-12-02", venue:"arXiv 2024"},
    {id:"2411.15858v2", title:"SVTRv2: CTC Beats Encoder-Decoder Models in Scene Text Recognition", authors:"Yongkun Du, Zhineng Chen…", date:"2024-11-24", venue:"arXiv 2024"},
    {id:"2411.15585v1", title:"Boosting Semi-Supervised Scene Text Recognition via Viewing and Summarizing", authors:"Yadong Qu, Yuxin Wang…", date:"2024-11-23", venue:"arXiv 2024"},
    {id:"2411.11219v2", title:"Relational Contrastive Learning and Masked Image Modeling for Scene Text Recognition", authors:"Tiancheng Lin, Jinglei Zhang…", date:"2024-11-18", venue:"arXiv 2024"},
    {id:"2410.11538v1", title:"MCTBench: Multimodal Cognition towards Text-Rich Visual Scenes Benchmark", authors:"Bin Shan, Xiang Fei…", date:"2024-10-15", venue:"arXiv 2024"}
  ]},
  {name:"Semantic Scholar", icon:"📚", type:"builtin", resolved:true, url:"semanticscholar.org", desc:"AI 检索 + TL;DR + 引文图谱", mock:[
    {id:"S2-1", title:"PP-OCR: A Practical Ultra Lightweight OCR System", authors:"Yuning Du et al.", date:"2020-09", venue:"arXiv 2020", note:"TL;DR: 超轻量三段式 OCR，模型仅 3.5M"},
    {id:"S2-2", title:"TrOCR: Transformer-based OCR with Pre-trained Models", authors:"Minghao Li et al.", date:"2021-09", venue:"arXiv 2021", note:"TL;DR: ViT+RoBERTa 端到端文本识别"},
    {id:"S2-3", title:"MASTER: Multi-Aspect Non-local Network for Scene Text Recognition", authors:"Ning Lu et al.", date:"2019-10", venue:"Pattern Recognition 2021", note:"TL;DR: 多角度编码器+Transformer 解码"}
  ]},
  {name:"ACL Anthology", icon:"📖", type:"builtin", resolved:true, url:"aclanthology.org", desc:"NLP/计算语言学官方论文集", mock:[
    {id:"A1", title:"LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking", authors:"Yupan Huang et al.", date:"2022-04", venue:"ACL 2022"},
    {id:"A2", title:"Donut: Document Understanding Transformer without OCR", authors:"Geewook Kim et al.", date:"2022-11", venue:"ECCV 2022"}
  ]},
  {name:"OpenReview", icon:"🔓", type:"builtin", resolved:true, url:"openreview.net", desc:"NeurIPS/ICLR/ICML 评审中论文", mock:[
    {id:"OR1", title:"DocLLM: A layout-aware generative language model for multimodal document understanding", authors:"Dongsheng Wang et al.", date:"2024-01", venue:"NeurIPS 2024"}
  ]},
  {name:"百度学术", icon:"🔎", type:"builtin", resolved:true, url:"xueshu.baidu.com", desc:"百度学术 · 中文文献检索（已解析）", mock:[
    {id:"BD1", title:"PP-OCR: A Practical Ultra Lightweight OCR System（实用超轻量 OCR）", authors:"Yuning Du et al. · 百度", date:"2020-09", venue:"arXiv 2020", note:"检测+方向+识别三段式，3.5M 轻量"},
    {id:"BD2", title:"Real-time Scene Text Detection with Differentiable Binarization（DB 文本检测）", authors:"Minghui Liao et al.", date:"2019-07", venue:"AAAI 2020", note:"可微分二值化，实时场景文本检测"},
    {id:"BD3", title:"FOTS: Fast Oriented Text Spotting with a Unified Network", authors:"Xuebo Liu et al.", date:"2018-01", venue:"ICCV 2018", note:"检测与识别端到端统一网络"},
    {id:"BD4", title:"MASTER: Multi-Aspect Non-local Network for Scene Text Recognition", authors:"Ning Lu et al.", date:"2019-10", venue:"Pattern Recognition 2021", note:"多角度编码器+Transformer 解码"}
  ]},
  {name:"谷歌学术", icon:"🌐", type:"builtin", resolved:true, url:"scholar.google.com", desc:"Google Scholar · 全球学术检索（已解析）", mock:[
    {id:"GS1", title:"An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale", authors:"Alexey Dosovitskiy et al.", date:"2021-01", venue:"ICLR 2021", note:"ViT 视觉 Transformer 开山之作"},
    {id:"GS2", title:"End-to-End Object Detection with Transformers (DETR)", authors:"Nicolas Carion et al.", date:"2020-05", venue:"ECCV 2020", note:"集合预测端到端检测"},
    {id:"GS3", title:"TrOCR: Transformer-based OCR with Pre-trained Models", authors:"Minghao Li et al.", date:"2021-09", venue:"arXiv 2021", note:"ViT+RoBERTa 双 Transformer OCR"}
  ]}
],

/* ---------- 简介读写：用户可编辑，localStorage 覆盖默认（key: pm_intros = {paperId: text}） ---------- */
getIntro: function(p){
  try{
    var map = JSON.parse(localStorage.getItem('pm_intros')||'{}');
    if(map[p.id]) return map[p.id];
  }catch(e){}
  return p.intro || '';
},
setIntro: function(id, text){
  try{
    var map = JSON.parse(localStorage.getItem('pm_intros')||'{}');
    map[id] = text;
    localStorage.setItem('pm_intros', JSON.stringify(map));
    return true;
  }catch(e){ return false }
},

/* ---------- 引擎设置：默认配置 + 服务商模板（用户可在设置中心覆盖，localStorage: pm_settings） ---------- */
engineDefaults: {
  translate: { mode:'builtin', provider:'内置翻译引擎', url:'', key:'', model:'' },
  ocr:      { mode:'builtin', provider:'内置 OCR（PaddleOCR）', url:'', key:'', model:'' }
},
translateProviders: [
  {name:'OpenAI 兼容接口', base:'https://api.openai.com/v1',        model:'gpt-4o-mini'},
  {name:'DeepSeek',        base:'https://api.deepseek.com/v1',      model:'deepseek-chat'},
  {name:'智谱 GLM',        base:'https://open.bigmodel.cn/api/paas/v4', model:'glm-4-flash'},
  {name:'通义千问',        base:'https://dashscope.aliyuncs.com/compatible-mode/v1', model:'qwen-plus'},
  {name:'月之暗面 Kimi',   base:'https://api.moonshot.cn/v1',       model:'moonshot-v1-8k'}
],
ocrProviders: [
  {name:'PaddleOCR 服务',  base:'http://10.1.7.68:8088',            model:'PP-OCRv5'},
  {name:'通用 HTTP OCR',   base:'',                                 model:''}
],

/* ---------- 知识图谱数据（论文节点 + 概念节点 + 引用/关联边） ----------
   边方向：from 引用/关联 to；read=true 表示已在个人文献库 */
graphNodes: [
  {id:'p0', label:'Attention Is All You Need', year:2017, cites:128000, type:'paper', read:true,  tags:'Transformer·NLP'},
  {id:'p1', label:'ResNet',                    year:2016, cites:210000, type:'paper', read:true,  tags:'CNN·图像分类'},
  {id:'p2', label:'ViT',                       year:2021, cites:98000,  type:'paper', read:true,  tags:'Transformer·CV'},
  {id:'p3', label:'DETR',                      year:2020, cites:42000,  type:'paper', read:true,  tags:'Transformer·检测'},
  {id:'p4', label:'PP-OCR',                    year:2020, cites:7200,   type:'paper', read:true,  tags:'OCR·轻量'},
  {id:'p5', label:'TrOCR',                     year:2021, cites:3900,   type:'paper', read:true,  tags:'OCR·Transformer'},
  {id:'p6', label:'MASTER',                    year:2021, cites:1500,   type:'paper', read:true,  tags:'OCR·STR'},
  {id:'r1', label:'BERT',                      year:2018, cites:150000, type:'related', read:false, tags:'NLP·预训练'},
  {id:'r2', label:'GPT',                       year:2018, cites:90000,  type:'related', read:false, tags:'NLP·预训练'},
  {id:'r3', label:'RoBERTa',                   year:2019, cites:60000,  type:'related', read:false, tags:'NLP·预训练'},
  {id:'r4', label:'CRNN',                      year:2015, cites:9000,   type:'related', read:false, tags:'OCR·序列识别'},
  {id:'r5', label:'DB（可微分二值化）',        year:2019, cites:6000,   type:'related', read:false, tags:'OCR·检测'},
  {id:'r6', label:'Faster R-CNN',              year:2015, cites:75000,  type:'related', read:false, tags:'CV·检测'},
  {id:'r7', label:'SVTR',                      year:2022, cites:2800,   type:'related', read:false, tags:'OCR·Transformer'},
  {id:'r8', label:'CLIP',                      year:2021, cites:55000,  type:'related', read:false, tags:'多模态·预训练'},
  {id:'c1', label:'注意力机制', keywords:['attention','自注意力','注意力','self-attention'], type:'concept'},
  {id:'c2', label:'卷积网络 CNN', keywords:['cnn','卷积','图像分类','resnet'], type:'concept'},
  {id:'c3', label:'预训练-微调', keywords:['预训练','pretrain','微调','fine-tune','大模型'], type:'concept'},
  {id:'c4', label:'序列识别', keywords:['序列识别','str','文本识别','crnn','ocr'], type:'concept'},
  {id:'c5', label:'轻量化部署', keywords:['轻量化','移动端','部署','蒸馏','剪枝','量化'], type:'concept'}
],
graphEdges: [
  ['p2','p0'],['p2','p1'],                 // ViT 引用 Transformer、ResNet
  ['p3','p0'],['p3','p1'],['p3','r6'],     // DETR 引用 Transformer、ResNet，对比 Faster R-CNN
  ['p4','p1'],['p4','r5'],['p4','r4'],     // PP-OCR 基于 ResNet、DB、CRNN
  ['p5','p2'],['p5','p0'],['p5','r3'],     // TrOCR 基于 ViT、Transformer、RoBERTa
  ['p6','p0'],['p6','p1'],['p6','r4'],     // MASTER 引用 Transformer、ResNet、CRNN
  ['r1','p0'],['r2','p0'],['r3','p0'],     // BERT/GPT/RoBERTa 基于 Transformer
  ['r7','p0'],['r8','p2'],                 // SVTR 基于 Transformer；CLIP 基于 ViT
  ['p0','c1'],['p2','c1'],['p3','c1'],['p5','c1'],['p6','c1'],['r1','c1'],['r2','c1'],  // 注意力机制
  ['p1','c2'],['p4','c2'],['r6','c2'],['r4','c2'],['r5','c2'],                          // CNN
  ['p2','c3'],['p5','c3'],['r1','c3'],['r2','c3'],['r3','c3'],['r8','c3'],               // 预训练-微调
  ['p4','c4'],['p5','c4'],['p6','c4'],['r4','c4'],['r7','c4'],                            // 序列识别
  ['p4','c5'],['r5','c5']                                                                  // 轻量化
],

/* ---------- 社区演示数据（团队/用户/公开动态，首次进入社区页时预置到 localStorage） ---------- */
demoUsers: [
  {id:'u2', name:'刘华成', avatar:'👨‍💻', role:'算法工程师', dir:'OCR · 文档智能'},
  {id:'u3', name:'张德勋', avatar:'🧑‍🔬', role:'测试工程师', dir:'考试防作弊 · 行为识别'},
  {id:'u4', name:'李梅', avatar:'👩‍💼', role:'产品经理', dir:'AI 产品设计'},
  {id:'u5', name:'陈明', avatar:'🧑‍🏫', role:'研究员', dir:'Transformer · 多模态'},
],
demoTeams: [
  {id:'t1', name:'视觉识别攻关组', desc:'考试防作弊视觉检测技术攻关 · 每周共读两篇', owner:'刘华成', members:['刘华成','王工'], applications:[]},
  {id:'t2', name:'OCR 文档智能', desc:'OCR 与文档解析方向共读小组', owner:'张德勋', members:['张德勋'], applications:[]},
  {id:'t3', name:'多模态前沿', desc:'Transformer / 多模态大模型论文精读', owner:'陈明', members:['陈明','李梅'], applications:[]},
],
demoNotes: [
  {id:'dn1', uid:'u2', name:'刘华成', avatar:'👨‍💻', role:'算法工程师', paperId:4, kind:'note',
   text:'PP-OCR 的轻量级设计很值得学：检测+识别两阶段解耦，MobileNetV3 骨干 + CTC 解码，部署友好。我们做考试试卷 OCR 可以借鉴这个思路。',
   summary:'轻量级 OCR 系统，检测识别解耦，适合端侧部署。',
   visibility:'public', ts: 1723708800000, likes: 12, comments:[
     {name:'张德勋', text:'请问检测分支用的什么结构？', ts:1723712400000},
     {name:'刘华成', text:'DB 可微二值化 + 轻量骨干，回头我把笔记整理发群里', ts:1723716000000},
   ]},
  {id:'dn2', uid:'u3', name:'张德勋', avatar:'🧑‍🔬', role:'测试工程师', paperId:3, kind:'summary',
   text:'DETR 端到端目标检测：把检测建模为集合预测问题，去掉 NMS/Anchor，Transformer 编码器-解码器直接输出目标集合。',
   summary:'端到端检测，无 NMS/Anchor，匈牙利匹配损失。',
   visibility:'public', ts: 1723622400000, likes: 8, comments:[
     {name:'李梅', text:'和 YOLO 比训练收敛慢的问题解决了吗？', ts:1723626000000},
   ]},
  {id:'dn3', uid:'u4', name:'李梅', avatar:'👩‍💼', role:'产品经理', paperId:0, kind:'note',
   text:'Transformer 的并行性对工程效率提升巨大。产品角度：注意力机制可视化对用户理解论文很有帮助，建议阅读器加"注意力热力图"。',
   summary:'注意力机制可视化可作为阅读器差异化功能。',
   visibility:'public', ts: 1723536000000, likes: 21, comments:[]},
  {id:'dn4', uid:'u5', name:'陈明', avatar:'🧑‍🏫', role:'研究员', paperId:5, kind:'summary',
   text:'TrOCR 用 Transformer 直接做 OCR 序列生成，预训练 + 微调范式。对中文长文本识别效果值得测一下。',
   summary:'Transformer 序列生成的 OCR 新范式。',
   visibility:'public', ts: 1723449600000, likes: 5, comments:[
     {name:'刘华成', text:'已加精读队列，下周看', ts:1723453200000},
   ]},
  {id:'dn5', uid:'u2', name:'刘华成', avatar:'👨‍💻', role:'算法工程师', paperId:2, kind:'summary',
   text:'ViT 把图像切 patch 当 token 进 Transformer，证明纯 Transformer 也能在视觉任务上 SOTA（当时）。',
   summary:'图像 patch 序列化 + 纯 Transformer 视觉。',
   visibility:'public', ts: 1723363200000, likes: 15, comments:[]},
],
defaultAvatar: '🦉',
avatars: ['🦉','🎓','📚','🔬','🧠','💻','🎯','🚀','👨🔬','👩💻','📈','🧪'],
userDefaults: {name:'王工', email:'wang@seaskylight.com', idcard:'310101********1234', role:'技术负责人', avatar:'🦉', direction:'AI视觉识别、OCR、考试防作弊'},
getUser: function(){
  try{
    var u = JSON.parse(localStorage.getItem('pm_user')||'null');
    if(u && u.name){
      /* 兜底默认头像/角色/研究方向（老数据兼容） */
      if(!u.avatar) u.avatar = PM.defaultAvatar;
      if(!u.role) u.role = '普通用户';
      if(!u.direction) u.direction = PM.userDefaults.direction;
      return u;
    }
  }catch(e){}
  return PM.userDefaults;
},
setUser: function(u){
  try{ localStorage.setItem('pm_user', JSON.stringify(u)); return true }catch(e){ return false }
},
logout: function(){ try{ localStorage.removeItem('pm_user') }catch(e){} },

/* ---------- 界面中英切换（localStorage: pm_lang，个人中心切换） ---------- */
i18n: {
  zh: {
    nav_discover:'发现', nav_library:'文献库', nav_graph:'图谱', nav_vault:'知识库', nav_community:'社区交流',
    menu_profile:'👤 个人中心', menu_edit:'📝 修改资料', menu_logout:'🚪 退出登录',
    btn_edit:'📝 修改资料', btn_logout:'🚪 退出登录', btn_save:'💾 保存资料', btn_cancel:'取消', btn_read:'📖 阅读', btn_continue:'继续', btn_view:'查看', btn_import:'导入', btn_clear:'清空', btn_delete:'删除', btn_save_set:'💾 保存设置', btn_reset:'↩ 恢复默认', btn_test:'🔌 测试连接', btn_add:'添加', btn_upload:'📁 上传图片', btn_reset_av:'↩ 恢复默认', btn_ai_gen:'🤖 AI 生成', btn_ai_intro:'🤖 AI 生成简介', btn_edit_intro:'✏️ 简介', btn_star:'☆ 收藏', btn_starred:'⭐ 已收藏', btn_copy_cite:'📋 复制引用', btn_read_original:'📖 阅读原文', btn_read_paper:'📖 阅读论文', btn_import_one:'📥 导入此篇', btn_import_all:'✅ 批量导入全部', btn_import_mine:'📥 导入文献', btn_clear_one:'清空此篇',
    t_profile:'个人中心', t_vault:'个人论文知识库', t_library:'文献库', t_graph:'知识图谱', t_discover:'发现',
    lang_label:'界面语言', lang_zh:'中文', lang_en:'English',
    pf_prefs:'⚙ 偏好设置', pf_edit:'📝 修改个人资料', pf_info:'🪪 个人资料', pf_recent:'🕘 最近阅读', pf_notes:'📝 我的笔记', pf_stars:'⭐ 我的收藏', pf_lang:'🌐 界面语言', pf_engine_t:'🈶 翻译引擎', pf_engine_o:'🔍 OCR 识别引擎', pf_cur_lang:'当前语言：', pf_stat_read:'已读论文', pf_stat_note:'笔记 / 高亮', pf_stat_min:'阅读时长(分)', pf_stat_q:'AI 提问次数', pf_tip_title:'基于你的研究方向', pf_tip_direct:'点「阅读」直接开始', pf_tip_nomatch:'暂无直接匹配文献，可在收藏网站检索或上传导入相关论文', pf_tip_ai:'用「AI 对话」问论文中你不确定的设计选择，比反复读原文更快',
    lib_tab_mine:'📚 我的文献', lib_tab_browse:'⭐ 收藏网站', lib_tab_reader:'📖 阅读器', lib_tab_import:'📥 导入文献',
    lib_cat_all:'全部', lib_cat_title:'论文类别（文件夹）', lib_filter_status:'状态', lib_filter_year:'年份', lib_filter_tag:'标签', lib_sort:'排序', lib_sort_time:'最近', lib_search_ph:'搜索我的文献…', lib_empty:'暂无文献',
    rd_detail:'📋 论文详情', rd_original:'📖 原文', rd_title:'📖 阅读器', rd_pick:'选择论文…', rd_not_started:'未开始阅读', rd_continue:'⏩ 继续阅读：', rd_last_read:'（上次读到 ', rd_reading:'正在阅读：', rd_read_pct:'已读 ', rd_ai_summary:'🤖 AI 精读总结', rd_core:'💡 核心观点', rd_problem:'研究问题', rd_method:'方法要点', rd_result:'主要结果', rd_limit:'结论与局限', rd_abs:'📄 摘要（中英对照）', rd_abs_zh:'中文', rd_abs_en:'原文', rd_glossary:'📖 术语表', rd_related:'🔗 相关论文', rd_related_ext:'外部文献', rd_notes:'条笔记', rd_ai_qa:'AI 问答', rd_outline:'大纲', rd_notes_panel:'笔记', rd_engine:'引擎', rd_mode_original:'原文', rd_mode_both:'中英对照', rd_mode_zh:'全译文', rd_search_ph:'搜索章节/关键词…',
    br_title:'🌐 收藏网站', br_default_tip:'🔖 已为您预置 6 个默认收藏网站（新注册用户自动获得）', br_default:'默认', br_custom:'自定义', br_search_ph:'搜索该站论文…', br_embed:'🌐 嵌入访问', br_search_view:'站内检索', br_import:'导入表单', br_import_checked:'✅ 导入选中', br_no_results:'暂无结果', br_detail_empty:'点击左侧检索结果在右侧查看论文详情',
    imp_title:'📥 导入文献', imp_upload:'📤 点击选择文件上传（单个或批量）', imp_upload_tip:'支持 PDF / DOCX / TXT · 可多选 · 每个文件自动生成一张资料卡', imp_pick_title:'标题（默认取文件名）', imp_cat:'所属类别（文件夹）', imp_status:'阅读状态', imp_tags:'标签（点击多选，可自定义）', imp_new_tag:'自定义标签，回车添加…', imp_intro:'简介（用于快速了解论文内容）', imp_intro_ph:'一句话说明这篇论文讲什么…', imp_auto_title:'自动识别标题，可修改', imp_remove:'移除', imp_ready:'个文件待导入', imp_done:'已导入「', imp_to:'→ 类别「', imp_status_to:'」· 状态「', imp_tag:'」· 标签：',
    vault_cards:'📚 已读论文 · AI 知识卡片', vault_terms:'📖 术语库（跨论文沉淀）', vault_notes:'💬 我的笔记（按论文聚合）', vault_export:'📤 导出 Obsidian', vault_stats:'📊 知识资产统计', vault_empty_notes:'暂无笔记', vault_note_count:'条笔记', vault_assets:'知识资产', vault_cards_stat:'知识卡片', vault_terms_stat:'术语积累', vault_notes_stat:'笔记', vault_hl_stat:'高亮', vault_prog_stat:'平均精读进度',
    idx_search_ph:'搜索论文、作者、研究方向…', idx_recommend:'🎯 为你推荐', idx_hot:'🔥 本周热榜', idx_import:'导入文献', idx_no_result:'未找到相关论文', idx_read:'阅读', idx_detail:'详情',
    graph_title:'🕸 知识图谱', graph_search_ph:'搜索知识点 / 论文 / 概念…', graph_legend_read:'已读论文', graph_legend_related:'相关论文', graph_legend_concept:'概念', graph_center:'中心论文',
    pager_total:'共 ', pager_pages:' 条 · ', pager_page:'/', pager_per:'每页 ', pager_per_unit:' 条',
    lang_cur:'当前语言：'
  },
  en: {
    nav_discover:'Discover', nav_library:'Library', nav_graph:'Graph', nav_vault:'Knowledge', nav_community:'Community',
    menu_profile:'👤 Profile', menu_edit:'📝 Edit Profile', menu_logout:'🚪 Logout',
    btn_edit:'📝 Edit Profile', btn_logout:'🚪 Logout', btn_save:'💾 Save', btn_cancel:'Cancel', btn_read:'📖 Read', btn_continue:'Continue', btn_view:'View', btn_import:'Import', btn_clear:'Clear', btn_delete:'Delete', btn_save_set:'💾 Save Settings', btn_reset:'↩ Reset', btn_test:'🔌 Test', btn_add:'Add', btn_upload:'📁 Upload Image', btn_reset_av:'↩ Reset', btn_ai_gen:'🤖 AI Generate', btn_ai_intro:'🤖 AI Intro', btn_edit_intro:'✏️ Intro', btn_star:'☆ Star', btn_starred:'⭐ Starred', btn_copy_cite:'📋 Copy Citation', btn_read_original:'📖 Read', btn_read_paper:'📖 Read Paper', btn_import_one:'📥 Import', btn_import_all:'✅ Import All', btn_import_mine:'📥 Import Papers', btn_clear_one:'Clear',
    t_profile:'Profile', t_vault:'My Knowledge Base', t_library:'Library', t_graph:'Knowledge Graph', t_discover:'Discover',
    lang_label:'Language', lang_zh:'中文', lang_en:'English',
    pf_prefs:'⚙ Preferences', pf_edit:'📝 Edit Profile', pf_info:'🪪 Profile Info', pf_recent:'🕘 Recent Reading', pf_notes:'📝 My Notes', pf_stars:'⭐ My Favorites', pf_lang:'🌐 Language', pf_engine_t:'🈶 Translation Engine', pf_engine_o:'🔍 OCR Engine', pf_cur_lang:'Current language: ', pf_stat_read:'Papers Read', pf_stat_note:'Notes / Highlights', pf_stat_min:'Minutes Read', pf_stat_q:'AI Questions', pf_tip_title:'Recommendations by your research directions', pf_tip_direct:'in your Library — hit Read', pf_tip_nomatch:'No direct match; search favorite sites or upload a paper', pf_tip_ai:'Ask AI about design choices you are unsure of instead of re-reading',
    lib_tab_mine:'📚 My Papers', lib_tab_browse:'⭐ Favorite Sites', lib_tab_reader:'📖 Reader', lib_tab_import:'📥 Import Papers',
    lib_cat_all:'All', lib_cat_title:'Categories (folders)', lib_filter_status:'Status', lib_filter_year:'Year', lib_filter_tag:'Tag', lib_sort:'Sort', lib_sort_time:'Recent', lib_search_ph:'Search my papers…', lib_empty:'No papers yet',
    rd_detail:'📋 Paper Detail', rd_original:'📖 Original', rd_title:'📖 Reader', rd_pick:'Select paper…', rd_not_started:'Not started', rd_continue:'⏩ Continue: ', rd_last_read:' (last read ', rd_reading:'Reading: ', rd_read_pct:'read ', rd_ai_summary:'🤖 AI Summary', rd_core:'💡 Core Idea', rd_problem:'Problem', rd_method:'Methods', rd_result:'Key Results', rd_limit:'Limitations', rd_abs:'📄 Abstract (EN/ZH)', rd_abs_zh:'Chinese', rd_abs_en:'Original', rd_glossary:'📖 Glossary', rd_related:'🔗 Related Papers', rd_related_ext:'External', rd_notes:'notes', rd_ai_qa:'AI Q&A', rd_outline:'Outline', rd_notes_panel:'Notes', rd_engine:'Engine', rd_mode_original:'Original', rd_mode_both:'Dual', rd_mode_zh:'Translation', rd_search_ph:'Search sections…',
    br_title:'🌐 Favorite Sites', br_default_tip:'🔖 6 default sites preset for new users', br_default:'Default', br_custom:'Custom', br_search_ph:'Search this site…', br_embed:'🌐 Embed', br_search_view:'Search', br_import:'Import form', br_import_checked:'✅ Import Selected', br_no_results:'No results', br_detail_empty:'Click a result to view paper detail',
    imp_title:'📥 Import Papers', imp_upload:'📤 Click to upload file(s)', imp_upload_tip:'PDF / DOCX / TXT · multi-select OK · one form per file', imp_pick_title:'Title (from filename, editable)', imp_cat:'Category (folder)', imp_status:'Status', imp_tags:'Tags (click to select, custom OK)', imp_new_tag:'Custom tag, Enter to add…', imp_intro:'Intro (quick overview)', imp_intro_ph:'One sentence about this paper…', imp_auto_title:'title from filename, editable', imp_remove:'Remove', imp_ready:'file(s) pending', imp_done:'Imported ', imp_to:' → ', imp_status_to:' · ', imp_tag:' · tags: ',
    vault_cards:'📚 Read Papers · AI Cards', vault_terms:'📖 Glossary (across papers)', vault_notes:'💬 My Notes (by paper)', vault_export:'📤 Export to Obsidian', vault_stats:'📊 Knowledge Assets', vault_empty_notes:'No notes', vault_note_count:'notes', vault_assets:'Knowledge Assets', vault_cards_stat:'Cards', vault_terms_stat:'Terms', vault_notes_stat:'Notes', vault_hl_stat:'Highlights', vault_prog_stat:'Avg Progress',
    idx_search_ph:'Search papers, authors, directions…', idx_recommend:'🎯 Recommended for You', idx_hot:'🔥 Hot This Week', idx_import:'Import Papers', idx_no_result:'No matching papers', idx_read:'Read', idx_detail:'Detail',
    graph_title:'🕸 Knowledge Graph', graph_search_ph:'Search knowledge / papers / concepts…', graph_legend_read:'Read', graph_legend_related:'Related', graph_legend_concept:'Concept', graph_center:'Center Paper',
    pager_total:'', pager_pages:' items · p.', pager_page:'/', pager_per:'per page ', pager_per_unit:'',
    lang_cur:'Current language: '
  }
},
getLang: function(){ try{ return localStorage.getItem('pm_lang')==='en' ? 'en' : 'zh' }catch(e){ return 'zh' } },
setLang: function(l){ try{ localStorage.setItem('pm_lang', l) }catch(e){} },
t: function(key){
  var lang = PM.getLang();
  var d = PM.i18n[lang] || PM.i18n.zh;
  return d[key] !== undefined ? d[key] : key;
},
applyI18n: function(){
  if(PM.getLang()==='zh') return;
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var k = el.getAttribute('data-i18n');
    var v = PM.t(k);
    if(v && v !== k) el.innerHTML = v;
  });
},

/* ---------- 用户级收藏网站：新注册用户自动获得默认收藏网站（按用户隔离，key: pm_sources_<email>） ---------- */
getUserSources: function(){
  var u = PM.getUser();
  var key = 'pm_sources_' + (u.email || 'default');
  try{
    var s = JSON.parse(localStorage.getItem(key)||'null');
    if(s && s.length) return s;
  }catch(e){}
  /* 首次访问（含新注册用户）：预置 6 个默认收藏网站 */
  var defaults = PM.browseSources.map(function(s){ return JSON.parse(JSON.stringify(s)) });
  try{ localStorage.setItem(key, JSON.stringify(defaults)) }catch(e){}
  return defaults;
},
setUserSources: function(arr){
  var u = PM.getUser();
  var key = 'pm_sources_' + (u.email || 'default');
  try{ localStorage.setItem(key, JSON.stringify(arr)); return true }catch(e){ return false }
},

/* ---------- 个人中心数据 ---------- */
stats:{read:3,total:7,notes:12,hl:26,minutes:318,streak:9},
recent:[0,4,2],
notes:[
  {paper:0, text:"多头注意力 = 并行做 h 次注意力再拼接，等价于在不同表示子空间捕捉依赖", color:"y"},
  {paper:0, text:"位置编码是正弦函数，可外推到更长序列", color:"b"},
  {paper:4, text:"PP-OCR 三段式：检测 DB → 方向分类 → 识别 CRNN，轻量到 3.5M", color:"g"},
  {paper:1, text:"残差连接本质是让网络退化成浅层也不会变差，再逐步加深", color:"p"}
],
/* ---------- 论文类别（文件夹=大类别）与阅读状态 ---------- */
categories: ["图像分类","目标检测","OCR","神经网络","多模态模型"],
statuses: ["在读","想读","读完"],
folders: ["全部","图像分类","目标检测","OCR","神经网络","多模态模型","收藏"],   // 兼容旧引用
}
