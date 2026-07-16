---
title: "Kanana-O lên production: hành trình tối ưu serving AI giọng nói của Kakao"
description: >
  Đội AI Engineering Kakao (hulk.5, steve.ai) chia sẻ trên Kakao Tech cách đưa
  mô hình omni Kanana-O vào dịch vụ thoại thời gian thực: server Kanana-Omni,
  shared memory, cascaded streaming, vLLM batching và API tương thích OpenAI.
date: 2026-07-16
lastmod: 2026-07-16
source_date: 2026-05-06
draft: false
author: "KoreaWiki Newsroom"
cover:
  image: images/2026/07/kakao-kanana-o-serving-optimization-2026-cover.jpg
  alt: "Sơ đồ / minh họa hành trình tối ưu serving Kanana-O của Kakao Tech"
  caption: "Kanana-O serving — Ảnh: Kakao Tech"
tags:
  - kakao
  - kanana
  - ai
  - tech
  - kanana-o
categories:
  - News
  - Digital
keywords:
  - kakao
  - kanana-o
  - kanana-omni server
  - serving
  - multimodal
  - vLLM
  - 카나나
slug: kanana-o-len-production-hanh-trinh-toi-uu-serving-ai-giong-noi-cua-kakao
faq:
  - q: "Kanana-O là gì?"
    a: >
      Mô hình **multimodal (omni)** của Kakao: hiểu **text, ảnh, audio** và trả
      lời bằng **text + giọng nói** tự nhiên. Bài Kakao Tech mô tả hành trình
      đưa model này lên **production** thoại thời gian thực.
  - q: "Kanana-Omni Server khác gì so với framework serving thông thường?"
    a: >
      Đội Kakao tự xây server phục vụ pipeline **Thinker → Talker → VoiceBox**
      (truyền **embedding** giữa các stage, streaming audio). Trong benchmark
      nội bộ với **64 user đồng thời**, throughput tương đối đạt **1,6×** so
      với **vllm-omni** (baseline 1,0).
  - q: "Ba bottleneck chính được xử lý thế nào?"
    a: >
      (1) **Truyền dữ liệu** giữa component: pool **shared memory** + **CUDA
      IPC**; (2) **Độ trễ tuần tự**: **Cascaded Streaming Pipeline**; (3)
      **Đồng thời / GPU**: tách process vLLM, **continuous batching**, FastAPI
      **workers=1** + async.
  - q: "Latency-First và Quality-First khác nhau ra sao?"
    a: >
      Khác **kích thước chunk** của VoiceBox: Latency-First (chunk nhỏ, phản
      hồi nhanh, chất lượng vừa) cho chat thời gian thực; Quality-First (chunk
      lớn, chậm hơn, âm thanh tự nhiên hơn) cho TTS / tạo nội dung. Client chọn
      theo request.
---

Trên blog kỹ thuật **Kakao Tech** (카카오테크), hai kỹ sư thuộc đội **AI
Engineering** — **hulk.5** và **steve.ai** — đã đăng bài viết kỹ thuật dài ngày
**6 tháng 5 năm 2026** kể lại hành trình đưa mô hình AI omni
**Kanana-O (카나나-오 / kanana-o)** từ giai đoạn huấn luyện sang **dịch vụ thoại
thời gian thực**. Trọng tâm không phải “model đạt bao nhiêu điểm benchmark lab”,
mà là chuỗi quyết định kỹ thuật khi phải **stream giọng nói** cho người dùng thật:
độ trễ trăm mili-giây, nhiều request đồng thời, GPU memory hạn hẹp, và an toàn
vận hành khi một process chết.

Bài viết cũng giới thiệu server tự xây **Kanana-Omni Server** — lớp serving được
thiết kế riêng cho pipeline ba giai đoạn của Kanana-O, thay vì chỉ bọc một endpoint
inference generic.

![Minh họa cover bài Kanana-O serving trên Kakao Tech](/images/2026/07/kakao-kanana-o-serving-optimization-2026-cover.jpg)
*Nguồn ảnh: Kakao Tech — https://tech.kakao.com/posts/821*

## Ai viết và bối cảnh sản phẩm

Theo mô tả tác giả trên Kakao Tech:

- **hulk.5** làm việc lâu năm với pipeline AI của Kakao — từ tinh chỉnh dữ liệu,
  modeling, học model, phát triển dịch vụ đến quản lý team. Hiện tại anh tập trung
  **tối ưu serving multimodal** trong đội AI Engineering.
- **steve.ai** (Steve) thuộc cùng đội, phụ trách **tối ưu model** và **hiệu năng
  serving**, với mục tiêu dịch vụ AI ổn định hơn cho người dùng cuối.

Kanana-o được mô tả là mô hình **multimodal**: hiểu tổng hợp **text, ảnh và
audio**, rồi trả lời bằng **text và giọng nói** tự nhiên. Kakao Tech có bài giới
thiệu chi tiết model trước đó (posts/702); bài 821 là “phần hai” mang tính
**engineering production** — sau khi model “xong”, làm sao để **lên dịch vụ**.

Tại thời điểm viết, team cho biết Kanana-O đang **beta test**: các tối ưu trong
bài vẫn tiếp tục được phát hiện và chỉnh sửa.

## Tóm tắt nhanh (TL;DR)

Ba câu tóm theo đúng tinh thần bài gốc:

1. **Kanana-o** xử lý nhiều modality đầu vào và sinh cả text lẫn giọng.
2. **Huấn luyện model** và **phục vụ người dùng realtime** là hai bài toán khác
   nhau: lab có thể chạy tuần tự; production đòi latency, concurrency và
   streaming không đứt.
3. **Kanana-Omni Server** là kết quả tự xây khi framework generic không khớp
   pipeline Thinker → Talker → VoiceBox; các kỹ thuật chính gồm shared memory /
   CUDA IPC, cascaded streaming, process isolation + vLLM continuous batching,
   FastAPI `workers=1` + async, Latency-First/Quality-First, warm-up,
   watermark, và API tương thích OpenAI.

Tham khảo thêm: [giới thiệu Kanana-o trên Kakao Tech](https://tech.kakao.com/posts/702).

## Model xong chưa đủ — serving là chuyện khác

Pipeline nội bộ Kanana-O, theo bài, gồm **ba component** với vai trò tách bạch:

| Component | Vai trò kỹ thuật |
|-----------|------------------|
| **Thinker** | LLM multimodal: hiểu input (text/ảnh/audio), sinh text / hidden state |
| **Talker** | Nhận **embedding** từ Thinker, sinh **token giọng** theo từng bước |
| **VoiceBox** | Ghép token thành **waveform** audio người nghe được (vocoder-like) |

Trong môi trường nghiên cứu, “chạy xong Thinker rồi mới Talker rồi mới VoiceBox”
là đủ để ra demo. Production thì khác hẳn vì người dùng và hạ tầng áp thêm ràng
buộc:

- **Latency cảm nhận:** user kỳ vọng **tiếng trả lời đầu** trong khoảng **vài trăm
  mili-giây**, không phải chờ cả câu text xong mới có âm thanh.
- **Concurrency:** server phải phục vụ **nhiều session đồng thời**, không phải
  một request đơn lẻ trên máy lab.
- **Streaming liên tục:** text generation và audio synthesis phải **đan xen**,
  không “câm” giữa các stage.
- **GPU heterogeneous:** mỗi component có **đặc tính bộ nhớ và compute** khác
  nhau; gộp bừa có thể OOM hoặc under-utilize.

Bài Kakao Tech khung lại toàn bộ như một **nhật ký gỡ bottleneck**: mỗi phần sau
là một nút thắt và cách team xử lý.

## Vì sao framework generic không đủ?

### Lúc bắt đầu, chưa có “khung sườn” phù hợp

Khi khởi động **Kanana-Omni Server**, các tác giả viết rằng **chưa có framework
đa năng** sẵn sàng cho đúng bài toán: ba model **trao đổi dữ liệu async**, đồng
thời **stream audio realtime**. Việc cần làm không chỉ là “bọc model bằng REST
API”, mà là **thiết kế luồng dữ liệu giữa các stage**.

Trong quá trình phát triển, framework multimodal kiểu **vllm-omni** bắt đầu xuất
hiện, nhưng team **không chọn** vì pipeline Kanana-O **không khớp** các giả định
của framework generic.

### Ba điểm framework khó “cover”

**1) Thinker → Talker truyền embedding, không phải token ID**

Serving LLM thông thường: model xuất **token ID**, bước sau nạp lại token đó.
Với Kanana-O, Thinker sinh **vector hidden-state / embedding hàng nghìn chiều**
và phải chuyển **trực tiếp** sang Talker theo thời gian thực. Serialize qua mạng
hoặc copy xuống CPU rồi lên GPU lại tạo overhead lớn. Team implement hướng
**zero-copy**: ưu tiên chỉ truyền **metadata địa chỉ bộ nhớ** (block name / handle)
thay vì copy full tensor mỗi bước.

**2) Talker sản xuất, VoiceBox tiêu thụ bất đối xứng**

Talker tạo một lượng **speech token** mỗi step; VoiceBox thì đợi token **đủ
chunk** rồi mới synthesize audio. Tốc độ sản xuất và tiêu thụ **không cân** —
cần **buffer async** và logic chia chunk, không phải pipe 1-1 đơn giản.

**3) Input Talker “dài dần” theo thời gian**

Talker không chỉ nhận embedding text từ Thinker. Thứ tự điển hình theo bài:

- **Speaker embedding** (đặc trưng giọng người nói) vào trước
- Tiếp theo là output của Thinker
- Cộng dồn **embedding giọng các bước trước** do chính Talker sinh ra

Mỗi step, tensor input **tăng chiều dài**. Đây không phải vòng autoregressive
token chuẩn, nên pipeline input của framework generic khó biểu diễn gọn.

![Minh họa so sánh throughput serving](/images/2026/07/kakao-kanana-o-serving-optimization-2026-01.png)
*Benchmark tương đối (64 user đồng thời) — Ảnh: Kakao Tech*

Kết quả benchmark **tương đối** team công bố (cùng điều kiện **64 concurrent
users**):

| Hệ thống | Throughput tương đối |
|----------|----------------------|
| Naive implementation | **0,44** |
| vllm-omni | **1,0** (baseline) |
| **Kanana-Omni Server** | **1,6** |

Nói cách khác, server chuyên biệt đạt **khoảng 1,6 lần** throughput của
vllm-omni trong kịch bản đo; bản naive chỉ còn khoảng **0,44** baseline.

## Bottleneck 1: truyền dữ liệu giữa component

Thinker và Talker có thể chạy trên **GPU khác** và/hoặc **process khác**. Nếu
implement “ngây thơ”, mỗi lần chuyển embedding đi đường:

`Thinker (GPU0) → CPU → serialize → IPC → deserialize → CPU → Talker (GPU1)`

Lặp đường này **theo từng token / từng chunk** biến overhead serialize thành
**độ trễ người dùng cảm nhận được**.

### Pool shared memory pre-allocate

Giải pháp: lúc **start server**, allocate sẵn **pool block shared memory** ở cấp
OS. Runtime **không alloc/free** từng request (tránh fragmentation và jitter).
Thinker lấy block, ghi dữ liệu; Talker chỉ nhận **tên block + metadata kích
thước**, rồi map đọc **cùng vùng nhớ**.

![Shared memory pool giữa Thinker và Talker](/images/2026/07/kakao-kanana-o-serving-optimization-2026-02.png)
*Pool bộ nhớ dùng chung — Ảnh: Kakao Tech*

### CUDA IPC cho tensor trên GPU

Trong **cùng một node**, khi tensor đã nằm trên GPU, team dùng **CUDA IPC
(Inter-Process Communication)** để process khác mở handle GPU memory — **không
kéo Device → Host → Device**. Theo mô tả, hai lớp tối ưu (shared memory pool +
CUDA IPC) khiến inter-component transfer **thoát khỏi danh sách bottleneck**.

## Bottleneck 2: chạy tuần tự → trễ “tiếng đầu”

Nếu pipeline cứng: Thinker **xong hết** text → Talker **xong hết** token →
VoiceBox mới synthesize, thì người dùng **không nghe gì** cho đến cuối chuỗi.
Response dài có thể mất **vài giây**; trải nghiệm giống “hệ thống treo”.

![Pipeline tuần tự gây trễ phản hồi đầu](/images/2026/07/kakao-kanana-o-serving-optimization-2026-03.png)
*Tuần tự end-to-end — Ảnh: Kakao Tech*

### Cascaded Streaming Pipeline

Team tách Thinker và Talker thành **async task**, nối bằng **queue bất đồng bộ**.
Ngay khi Thinker xong **chunk đầu**, Talker đã có thể sinh speech token cho
chunk đó, trong khi VoiceBox **đồng thời** synthesize chunk trước nữa. Các stage
**chồng pha** như bánh răng — “cascaded streaming”.

Talker vẫn sinh token theo step; khi buffer đủ, VoiceBox mới biến thành
waveform. Mục tiêu rõ ràng: **rút ngắn thời gian tới byte audio đầu tiên**
(time-to-first-audio), không chỉ tối ưu tokens/giây trung bình.

![Cascaded streaming pipeline](/images/2026/07/kakao-kanana-o-serving-optimization-2026-04.png)
*Streaming chồng stage — Ảnh: Kakao Tech*

## Tách process: cách ly lỗi và hai engine vLLM

Thinker và Talker mỗi bên chạy như **engine vLLM** riêng: load model, quản lý
**KV cache**, scheduling inference. vLLM tự coi là một runtime inference “khép
kín”. Nếu **hai engine** cùng sống trong **một process**, dễ gặp xung đột
**CUDA context** hoặc can thiệp quản lý memory.

**Kanana-Omni Server** chọn: **mỗi engine một process**, mỗi process một CUDA
context. Cách tạo process: **`spawn`**, không **`fork`**.

- `fork` copy không gian nhớ parent → dễ “ô nhiễm” trạng thái GPU.
- `spawn` khởi động interpreter sạch hơn, giảm rủi ro state GPU lệch.

Lợi ích vận hành được nhấn mạnh: khi traffic cao làm Thinker **OOM chết**,
Talker và **API server chính** vẫn có thể đứng; restart từng engine độc lập
được — **fault isolation**.

## Continuous batching: để vLLM xếp hàng, server chỉ “đẩy request”

Sau khi tách process, bài toán tiếp theo là **throughput trong từng process**
khi nhiều user cùng lúc. Batch thủ công rất khó:

- **Thinker:** mỗi request multimodal khác kích thước (một ảnh, nhiều audio…) —
  gộp batch đòi padding → phí GPU.
- **Talker:** độ dài embedding tích lũy **khác nhau** theo request → batch tay
  cần đồng bộ phức tạp.

Hướng đi của team: **không tự viết logic batch chi tiết**; ủy quyền
**continuous batching** cho **scheduler vLLM**. Phía server tập trung **nạp
request vào engine càng nhanh càng tốt**.

Vòng lặp trong process (theo mô tả / pseudo-code bài gốc): nhận lệnh từ queue
(`input_q.get`), lập tức `asyncio.create_task(generate(...))` — **không chờ**
request trước xong mới nhận request sau. Mỗi task gọi `engine.generate()`;
vLLM gộp nhiều request trong forward pass nhưng trả kết quả theo `request_id`.
Task chỉ **yield** stream của đúng request mình.

![Vòng lặp request async vào vLLM](/images/2026/07/kakao-kanana-o-serving-optimization-2026-05.png)
*Đẩy request async vào engine — Ảnh: Kakao Tech*

vLLM cho phép cấu hình **trần số sequence đồng thời**; trong trần đó, scheduler
cân GPU memory và trạng thái request để ghép batch. Điều kiện tiên quyết: **API
server** cũng phải nhận concurrent request **không block** — dẫn đến phần
FastAPI dưới đây.

## FastAPI `workers=1` và chuỗi async end-to-end

### Vì sao không `workers=N`?

Kanana-Omni Server dựng trên **FastAPI + Uvicorn**. Web app thông thường hay
tăng worker process để scale. Serving model nặng thì khác:

- Mỗi Uvicorn worker nếu **tự load** vLLM/model → **nhân N lần** GPU memory và
  thời gian load.
- Thinker đã chiếm phần lớn VRAM → chỉ **2 worker** cũng dễ **không đủ memory**.
- Tách hẳn Thinker/Talker thành service qua **network** để scale worker thì mất
  zero-copy embedding (tensor float nghìn chiều mỗi step qua mạng).

Do đó cấu hình thực tế được mô tả: **`workers=1`**.

### Nguy cơ single worker

Một chỗ **sync block** trên event loop (CPU nặng, serialize, tensor host) có thể
làm **mọi user** chờ — kể cả request chỉ cần HTTP response nhẹ.

### Giải pháp: async chain từ API đến audio

Toàn bộ đường đi được tổ chức **async/await**: endpoint streaming →
thinker/talker tasks → voicebox stream. Không có “vách sync” giữa các tầng.

**CPU-bound** (serialize, một số tính toán tensor phía host) được đẩy sang
**thread pool**, để event loop chỉ **await** kết quả và tiếp tục interleave
request khác. Bài gốc cũng nhắc: nhiều kernel PyTorch nặng chạy C++ và **nhả
GIL**, nên thread pool hữu ích hơn so với thuần Python CPU.

**VoiceBox** là stage “nặng” VRAM; quá nhiều synthesize song song dễ OOM. Team
dùng **`asyncio.Semaphore`** giới hạn số job VoiceBox đồng thời — vượt trần thì
chờ, không sập memory.

Cascaded pipeline (create_task + queue) cũng nằm trên async chain này: **một
worker process** vẫn phục vụ nhiều session bằng **interleaving**.

## Cùng model, hai chiến lược: Latency-First vs Quality-First

Sau khi pipeline và concurrency ổn, team đối mặt trade-off sản phẩm:

| Nhu cầu | Ưu tiên |
|---------|---------|
| Chat / thoại realtime | **Tiếng đầu nhanh**, chấp nhận chất lượng vừa |
| Tạo nội dung / TTS | **Âm thanh tự nhiên hơn**, chấp nhận chậm hơn |

Đòn bẩy chính: **kích thước chunk VoiceBox**.

| Chế độ | Chunk | Tiếng đầu | Chất lượng | Tình huống |
|--------|-------|-----------|------------|------------|
| **Latency-First** | nhỏ | nhanh | vừa | realtime chat, chatbot |
| **Quality-First** | lớn | chậm hơn | cao | content generation, TTS |

Client chọn theo **từng request** (ví dụ payload JSON có `latency_first: true`,
`stream: true`, `model: "kanana-o"`). Nhờ đó **cùng server, cùng model, cùng
GPU** phục vụ được cả hai kịch bản — không cần deploy hai stack tách rời chỉ vì
trade-off chất lượng/tốc độ.

## Warm-up khi start và watermark giọng AI

### Chống cold start

Lần inference PyTorch **đầu tiên** thường chậm hơn nhiều lần sau (compile CUDA
kernel, pattern alloc bộ nhớ, v.v.). Nếu bỏ qua, **user đầu tiên** sau deploy
gánh toàn bộ chi phí. Team **warm-up VoiceBox** lúc start cho **cả hai mode**
Latency-First và Quality-First bằng **dummy token**; giai đoạn này cũng gắn với
**torch.compile** để ổn định hiệu năng từ request thật đầu tiên.

### Watermark “nghe không thấy”

Khi giọng AI ngày càng tự nhiên, câu hỏi “đây có phải AI không?” trở nên quan
trọng. **Kanana-Omni Server** **tự chèn watermark** vào **mọi** audio sinh ra:
mã định danh model được encode trong dải tần **người thường không nghe thấy**,
nhưng tool nội bộ có thể xác minh “có phải output Kanana-O”. Đây là lớp
**ethical / provenance**, không chỉ tối ưu tốc độ. Model watermark cũng được
warm-up với audio ngắn và dài để latency ổn định.

## API tương thích OpenAI Chat Completions

Dù serving nội bộ phức tạp, **mặt ngoài** được làm **100% tương thích** chuẩn
**OpenAI Chat Completions** — hệ sinh thái SDK/tooling quen thuộc với developer.

Hướng dùng theo bài (local):

- `base_url` trỏ `http://localhost:8000/v1`
- `model="kanana-o"`
- `modalities` chuyển **text** hoặc **text + audio** theo request
- `audio.voice` chọn preset (ví dụ `preset_spk_1`)
- Message multimodal: audio base64 + text instruction (ví dụ tóm tắt audio)

Developer **đổi endpoint** là tái sử dụng code OpenAI SDK cũ. Server còn
**validate input** và trả **error message cụ thể** khi request sai — yếu tố
vận hành thường bị bỏ quên nếu chỉ tối ưu “happy path”.

## Bài học team rút ra

### 1) Hiểu cấu trúc model → được phép tối ưu “chuyên biệt”

- Shared memory pool sized đúng vì team **biết** kích thước/dạng embedding
  Thinker→Talker.
- Cascaded pipeline vì **stage cố định** ba bước.
- Phân bổ GPU dựa trên **đo đạc** từng component.

Framework generic thường phải **giả định chưa biết trước** → thiết kế bảo thủ,
khó đạt cùng mức tối ưu.

### 2) Production không chỉ là tokens/giây

Ngoài throughput và latency inference, dịch vụ thật cần watermark, validate,
error handling, health monitoring, chống cold start… Những hạng mục này thường
**chỉ lộ ra sau khi model “học xong”**, và phải giải theo **yêu cầu dịch vụ**,
không theo paper.

### 3) Thu hẹp phạm vi để kiểm soát hệ thống

Kanana-Omni Server **chỉ** nhắm **voice dialogue serving cho Kanana-O**: không
multi-model generic, không image generation, không multi-node distributed trong
phạm vi bài. Đổi lại: codebase nhỏ hơn, engineer **nắm end-to-end** và vận hành
chặt hơn.

## Ý nghĩa với độc giả quan tâm hệ sinh thái Kakao AI

Bài 821 là **post-mortem kỹ thuật** (ở dạng blog kỹ sư), không phải thông cáo
marketing. Nó bổ sung góc nhìn “dưới nắp capo” cho các sản phẩm/truyền thông
Kanana mà Kakao đã công bố công khai ở kênh khác — ví dụ series video
**Kanana-original** giới thiệu năng lực omni, hay các cập nhật KakaoTalk gắn AI
trên client. Serving realtime là điều kiện để omni model **cảm thấy mượt** trong
hội thoại thật, chứ không chỉ đẹp trên demo.

Kanana-O vẫn **beta**; team khẳng định còn phát hiện và chỉnh tối ưu ngoài phạm
vi bài. Độc giả kỹ thuật nên coi số liệu throughput **1,6×** là **benchmark nội
bộ** trong điều kiện 64 concurrent users được mô tả, không ngoại suy thành
xếp hạng toàn ngành.

## Tác giả, nguồn và liên kết

- **hulk.5**, **steve.ai** — AI Engineering, Kakao
- Nguồn gốc: [Kakao Tech posts/821](https://tech.kakao.com/posts/821)
  (tiêu đề gốc: *음성 AI 모델을 프로덕션에 올리기까지: Kanana-O 서빙 최적화 여정*,
  ngày **2026-05-06**)
- Bài liên quan model: [Kakao Tech posts/702](https://tech.kakao.com/posts/702)

Trên KoreaWiki, có thể đọc thêm các bài cùng hệ Kakao/Kanana (liên kết cuối
bài): series Kanana-original và cập nhật KakaoTalk tích hợp AI trên PC.

Nguồn: Kakao Tech — https://tech.kakao.com/posts/821

{{< article-footer >}}
source: "Kakao Tech"
source_url: "https://tech.kakao.com/posts/821"
copyright: >
  Một phần nội dung tham khảo từ bài kỹ thuật
  [Kakao Tech — posts/821](https://tech.kakao.com/posts/821)
  (6/5/2026, hulk.5 & steve.ai). Ảnh minh họa thuộc Kakao Tech / Kakao.
  Bài KoreaWiki chỉ tổng hợp và biên tập tiếng Việt phục vụ độc giả — không thay
  thế tài liệu kỹ thuật hay tài liệu chính thức của Kakao.
external:
  - title: "Kakao Tech — Kanana-O 서빙 최적화 여정"
    url: "https://tech.kakao.com/posts/821"
  - title: "Kakao Tech — tìm hiểu thêm Kanana-o (posts/702)"
    url: "https://tech.kakao.com/posts/702"
internal:
  - title: "Kakao ra mắt series Kanana-original giới thiệu AI omni Kanana-o"
    url: "en/news/kakao-ra-mat-series-kanana-original-gioi-thieu-ai-omni-kanana-o/"
  - title: "KakaoTalk bản cập nhật 6: tóm tắt tin nhắn, ChatGPT for Kakao trên PC"
    url: "en/news/kakaotalk-ban-cap-nhat-6-tom-tat-tin-nhan-chatgpt-for-kakao-tren-pc/"
{{< /article-footer >}}
