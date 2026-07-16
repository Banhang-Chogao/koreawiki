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


Trên blog kỹ thuật **Kakao Tech** (카카오테크), hai kỹ sư **AI Engineering** **hulk.5** và **steve.ai**
công bố bài viết dài ngày **6 tháng 5 năm 2026** về hành trình đưa mô hình AI omni **Kanana-O (카나나-오
/ kanana-o)** từ giai đoạn huấn luyện sang **dịch vụ thoại thời gian thực** — kèm các kỹ thuật tối
ưu của server tự xây **Kanana-Omni Server**.

![Minh họa cover bài Kanana-O serving trên Kakao Tech](/images/2026/07/kakao-kanana-o-serving-optimization-2026-cover.jpg)
*Nguồn ảnh: Kakao Tech — https://tech.kakao.com/posts/821*

## Tóm tắt nhanh (TL;DR)

**Kanana-o** hiểu đồng thời **text · ảnh · audio** và phản hồi bằng **text + giọng nói**. Học model
và **phục vụ người dùng thật** là hai bài toán khác nhau. Bài viết tập trung các nút thắt kỹ thuật
khi stream thoại realtime, và cách **Kanana-Omni Server** xử lý chúng.

Tham khảo thêm giới thiệu model: [bài Kakao Tech liên quan về Kanana-o](https://tech.kakao.com/posts/702).

## Model xong chưa đủ — serving là chuyện khác

Pipeline nội bộ Kanana-O gồm **ba component**:

| Component | Vai trò |
|-----------|---------|
| **Thinker** | LLM multimodal: hiểu input, sinh text |
| **Talker** | Nhận embedding text, sinh **token giọng** tuần tự |
| **VoiceBox** | Ghép token thành **waveform** audio người nghe được |

Trong lab, chạy tuần tự ba stage là đủ. Production đòi hỏi thêm:

- Người dùng kỳ vọng **tiếng trả lời đầu** trong vài **trăm mili-giây**
- Server xử lý **nhiều request đồng thời**
- Text generation và **tổng hợp audio** phải **stream liên tục**, không “cắt khúc”
- Mỗi component có **đặc tính và dung lượng GPU** khác nhau

## Vì sao không chỉ bọc API bằng framework sẵn?

Khi bắt đầu **Kanana-Omni Server**, theo các tác giả, chưa có framework đa năng nào “cắm là chạy”
đúng pipeline 3 model **async**, stream audio realtime. Cần thiết kế **luồng dữ liệu giữa model**,
không chỉ wrap inference API.

Framework multimodal kiểu **vllm-omni** xuất hiện giữa chừng nhưng **không được chọn** vì không khớp pattern riêng của Kanana-O:

1. **Thinker → Talker truyền embedding, không phải token ID.** LLM thường xuất token rồi nạp lại; ở
đây hidden-state **hàng nghìn chiều** phải chuyển realtime. Thay vì serialize qua network hoặc copy
CPU, team implement **zero-copy** (chỉ truyền metadata địa chỉ bộ nhớ GPU khi có thể).

2. **Talker sản xuất, VoiceBox tiêu thụ bất đối xứng.** Talker sinh token từng bước; VoiceBox đợi **đủ chunk** rồi mới synthesize — cần **buffer async** và logic chia chunk.

3. **Input Talker không chuẩn autoregressive.** Speaker embedding + output Thinker + embedding giọng bước trước **tích lũy** — tensor input **dài dần mỗi step**, khó map vào pipeline input generic.

![Minh họa so sánh throughput serving](/images/2026/07/kakao-kanana-o-serving-optimization-2026-01.png)
*Benchmark tương đối (64 user đồng thời) — Ảnh: Kakao Tech*

| Hệ thống | Throughput tương đối (64 concurrent) |
|----------|--------------------------------------|
| Naive implementation | **0,44** |
| vllm-omni | **1,0** (baseline) |
| **Kanana-Omni Server** | **1,6** |

## Bottleneck 1: truyền dữ liệu giữa component

Thinker và Talker có thể chạy trên **GPU khác / process khác**. Đường “ngây thơ”:

`GPU0 → CPU → serialize → IPC → deserialize → CPU → GPU1`

Mỗi token đi đường này làm **latency cảm nhận** tăng.

### Pool shared memory pre-allocate

Lúc start server, OS-level **allocate sẵn** nhiều block shared memory; runtime **không alloc/free**. Thinker ghi block; Talker chỉ nhận **tên/metadata block** và đọc cùng địa chỉ.

![Shared memory pool giữa Thinker và Talker](/images/2026/07/kakao-kanana-o-serving-optimization-2026-02.png)
*Pool bộ nhớ dùng chung — Ảnh: Kakao Tech*

### CUDA IPC

Trong cùng node, tensor trên GPU truyền bằng **CUDA IPC** — tránh vòng **Device → Host → Device**. Hai tối ưu này khiến inter-component transfer **không còn là bottleneck** (theo mô tả trong bài).

## Bottleneck 2: chạy tuần tự gây trễ tiếng đầu

Nếu đợi Thinker xong hết rồi mới Talker, rồi mới VoiceBox, user **không nghe gì** cho đến khi cả pipeline kết thúc; response dài có thể vài giây và dễ bị hiểu nhầm là lỗi.

![Pipeline tuần tự gây trễ phản hồi đầu](/images/2026/07/kakao-kanana-o-serving-optimization-2026-03.png)
*Tuần tự end-to-end — Ảnh: Kakao Tech*

### Cascaded Streaming Pipeline

Thinker và Talker là **async task** nối bằng **queue**. Khi Thinker xong chunk đầu, Talker đã làm
token giọng chunk trước; VoiceBox đồng thời synthesize chunk cũ hơn — các stage **chồng lên nhau**
như bánh răng.

![Cascaded streaming pipeline](/images/2026/07/kakao-kanana-o-serving-optimization-2026-04.png)
*Streaming chồng stage — Ảnh: Kakao Tech*

## Tách process: cách ly lỗi và vLLM

Thinker và Talker mỗi bên là **engine vLLM** riêng (load model, KV cache, scheduler). Hai engine
trong **một process** dễ đụng **CUDA context** và quản lý memory. **Kanana-Omni Server** chạy chúng
bằng **process riêng** (`spawn`, không `fork` — fork copy memory parent dễ conflict CUDA).

Lợi ích vận hành: Thinker **OOM** khi traffic cao **không kéo sập** Talker và API server chính; restart engine độc lập được.

## Continuous batching — để vLLM xếp batch

Batch thủ công khó vì:

- Thinker: kích thước **ảnh/audio** mỗi request khác nhau, padding lãng phí GPU
- Talker: độ dài embedding tích lũy **khác nhau** theo request

Giải pháp: **ủy quyền** continuous batching cho **scheduler vLLM**; phía server **đẩy request
nhanh** vào engine (fire-and-forget `asyncio.create_task` ngay khi lấy lệnh từ queue). Kết quả theo
`request_id`; mỗi task chỉ stream response của mình.

![Vòng lặp request async vào vLLM](/images/2026/07/kakao-kanana-o-serving-optimization-2026-05.png)
*Đẩy request async vào engine — Ảnh: Kakao Tech*

## FastAPI workers=1 và chuỗi async end-to-end

Server dựng trên **FastAPI + Uvicorn**. Multi-worker (`workers=N`) sẽ **load N lần model**, nhân GPU
memory và thời gian load; với Thinker đã chiếm phần lớn VRAM, **multi-worker thực tế không khả
thi**. Tách model ra server riêng qua network thì mất lợi thế **zero-copy embedding**.

Rủi ro `workers=1`: một chỗ **block** (CPU/tensor sync trên event loop) khiến **toàn bộ user** đứng. Cách xử lý:

- Toàn đường xử lý từ API đến Thinker/Talker/VoiceBox là **async/await**
- Việc **CPU-bound** (serialize, một số tensor work) đẩy **thread pool** để giữ event loop
- **VoiceBox** (vocoder “nặng” VRAM) giới hạn song song bằng **`asyncio.Semaphore`** để tránh OOM

Cascaded pipeline cũng nằm trên async chain này — **một worker** vẫn **interleave** nhiều request.

## Latency-First vs Quality-First

Cùng model và GPU, khác **kích thước chunk VoiceBox**:

| Chế độ | Chunk | Tiếng đầu | Chất lượng | Tình huống |
|--------|-------|-----------|------------|------------|
| **Latency-First** | nhỏ | nhanh | vừa | chat realtime, chatbot |
| **Quality-First** | lớn | chậm hơn | cao | tạo nội dung, TTS |

Client chọn theo request (ví dụ cờ `latency_first: true` trong payload JSON) để **cùng server** phục vụ cả hội thoại nhanh và TTS chất lượng cao.

## Warm-up và watermark giọng AI

**Cold start:** lần inference PyTorch đầu (compile CUDA kernel, alloc…) chậm gấp nhiều lần các lần
sau. Server **warm-up VoiceBox** (cả Latency-First và Quality-First) bằng dummy token khi start; áp
dụng cả **torch.compile** ở giai đoạn này.

**Watermark:** mọi audio sinh ra được **gắn watermark tự động** (mã định danh model trong dải người
thường **không nghe thấy**), hỗ trợ nhận diện “có phải giọng Kanana-O” bằng tool nội bộ — phục vụ
**hệ sinh thái AI có trách nhiệm**. Model watermark cũng được warm-up (audio ngắn/dài) để latency ổn
định từ request đầu.

## API tương thích OpenAI Chat Completions

Kanana-Omni Server implement **100% tương thích** chuẩn **OpenAI Chat Completions** (đổi `base_url`
là dùng lại SDK). Hỗ trợ `modalities` text / text+audio, chọn voice preset, validate input và trả
**error message cụ thể** khi request sai.

Ví dụ hướng dùng (theo bài gốc): endpoint local `http://localhost:8000/v1`, model `kanana-o`, message multimodal (audio base64 + text yêu cầu tóm tắt audio).

## Bài học từ production (theo tác giả)

1. **Hiểu cấu trúc model** giúp chọn giải pháp **chuyên biệt** (shared memory sized đúng, cascade cố định, phân bổ GPU đo được) thay vì luôn generic “an toàn quá mức”.
2. **Production không chỉ là tokens/s:** watermark, validate, error handling, health, anti-cold-start quyết định **độ ổn định** dịch vụ.
3. **Thu hẹp phạm vi** (chỉ voice-dialogue serving cho Kanana-O — không multi-model, không image gen, không multi-node) giúp codebase nhỏ, engineer **nắm và kiểm soát** toàn hệ.

Kanana-O đang **beta test**; team cho biết còn phát hiện và chỉnh tối ưu thêm.

## Tác giả và nguồn

- **hulk.5** — AI Engineering, Kakao: kinh nghiệm pipeline AI từ data đến modeling và service; hiện tối ưu serving multimodal.
- **steve.ai** — AI Engineering: tối ưu model và hiệu năng serving.
- Nguồn: [Kakao Tech — posts/821](https://tech.kakao.com/posts/821) (6/5/2026).

Độc giả KoreaWiki quan tâm AI Kakao có thể xem thêm các bài liên quan trên site về series Kanana-original và bản cập nhật KakaoTalk tích hợp AI (liên kết cuối bài).

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
