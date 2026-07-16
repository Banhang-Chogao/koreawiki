---
title: 'Từ sinh viên đến kỹ sư Kakao: Hành trình học DB, bảo mật và AI qua chương
  trình onboarding cho tân binh'
description: 40 tân binh Kakao tốt nghiệp chương trình onboarding kỹ thuật, học cách
  thiết kế database chịu tải, bảo mật ở cấp độ production, và biến AI thành hệ thống
  có thể vận hành — thay vì chỉ chạy theo đáp án đúng trong sách vở.
date: 2026-07-16
lastmod: 2026-07-16
source_date: 2026-03-13
slug: tu-sinh-vien-den-ky-su-kakao-hanh-trinh-hoc-db-bao-mat-va-ai-qua-chuong-trinh-onboarding-cho-tan-binh
categories:
- tech
- feature
tags:
- Kakao
- onboarding
- database
- security
- AI
- new-krew
- career
- engineering
draft: false
keywords:
- Kakao technical onboarding
- New Krew
- database production
- AI agent architecture
- security engineering
- RAG MCP
- Hàn Quốc
author: zephy.r, mint.pearl, theo.cha, rowan.ko (Kakao Tech)
cover:
  image: images/2026/07/kakao-new-krew-onboarding-2026-cover.jpg
  alt: 'Bốn tác giả bài viết hồi tưởng quá trình onboarding tại Kakao: zephy.r, mint.pearl,
    theo.cha và rowan.ko'
  caption: 'Ảnh: Kakao Tech — bốn thành viên đội ngũ tân binh Krew viết bài hồi tưởng'
faq:
- q: Chương trình onboarding kỹ thuật của Kakao kéo dài bao lâu và có những nội dung
    gì?
  a: 'Bài viết là hồi tưởng của bốn tân binh Krew (đợt tuyển dụng mới nhất của Kakao)
    sau khi hoàn thành chương trình technical onboarding. Nội dung gồm ba mảng chính:
    Database (thiết kế schema, index, replication), Security & IT (bảo mật API, DDoS,
    CERT) và AI (agent architecture, RAG, MCP). Tổng cộng 40 tân binh tham gia.'
- q: Tại sao Kakao không dùng物理 Foreign Key trong môi trường production?
  a: Theo chia sẻ của đội ngũ Krew, physical FK gây ra vấn đề về Lock, hiệu năng và
    tính linh hoạt trong môi trường có traffic lớn và thay đổi thường xuyên. Thay
    vào đó, Kakao chuyển trách nhiệm đảm bảo toàn vẹn dữ liệu lên tầng Application,
    kèm theo test và logic bù chặt chẽ hơn.
- q: Kakao dạy gì về AI cho lập trình viên mới?
  a: Tân binh được học rằng AI Agent là 'design chứ không phải model'. Họ thực hành
    Prompt Chaining, Few-shot, Routing, Multi-Agent architecture, RAG (Retrieval-Augmented
    Generation) và MCP (Model Context Protocol). Trọng tâm là kiểm soát đầu ra xác
    suất của LLM bằng thiết kế hệ thống thay vì cầu may.
- q: Bài học lớn nhất mà các tân binh Kakao rút ra từ khóa onboarding là gì?
  a: Sự chuyển đổi tư duy từ 'sinh viên đi tìm đáp án đúng' sang 'kỹ sư cân bằng giữa
    lý thuyết và vận hành thực tế'. Họ học được rằng thiết kế hoàn hảo trên lý thuyết
    chưa chắc đã là thiết kế tốt trong môi trường production — điều quan trọng là
    khả năng chịu tải, chi phí vận hành và an toàn bảo mật.
- q: Bảo mật được dạy như thế nào trong chương trình?
  a: Bảo mật không chỉ là lý thuyết. Tân binh thực hành trực tiếp các cuộc tấn công
    API để hiểu góc nhìn của hacker, tìm hiểu về phòng thủ DDoS, Rate Limit, và nhấn
    mạnh rằng bảo mật không phải việc 'làm một lần rồi thôi' mà phải là giá trị mặc
    định xuyên suốt vòng đời phát triển.
---
Khi còn ngồi trên ghế đại học, bạn được dạy rằng Foreign Key phải được ràng buộc chặt, rằng chuẩn hóa dữ liệu là đức hạnh, và rằng code chạy đúng là đủ. Nhưng khi bước vào môi
trường production với hàng triệu người dùng, những chân lý ấy bắt đầu lung lay.

40 tân binh vừa trúng tuyển kỳ tuyển dụng tập trung của **Kakao** — được gọi là *New Krew* — đã hoàn thành chương trình technical onboarding kéo dài, bao gồm ba chủ đề lớn:
Database, Security & IT, và AI. Bốn thành viên trong số họ — **zephy.r** (biên tập dữ liệu), **mint.pearl** (nền tảng DB), **theo.cha** (dữ liệu bản đồ-giao thông) và **rowan.ko**
(phát triển KakaoTalk iOS) — đã cùng viết bài hồi tưởng về hành trình từ "sinh viên đi tìm đáp án đúng" thành "kỹ sư biết cân bằng giữa lý thuyết và thực tế vận hành."

![Sơ đồ tư duy về thiết kế database: từ lý thuyết đến thực hành](/images/2026/07/kakao-new-krew-onboarding-2026-01.png)
*Minh họa: Kakao Tech — quá trình chuyển đổi tư duy thiết kế database từ học thuật sang production*

## Database: Từ "đi tìm đáp án đúng" đến "thiết kế cho sự thay đổi"

Phần Database là nơi các tân binh trải nghiệm cú sốc nhận thức lớn nhất. Trên giảng đường đại học, vẽ ERD và gắn Foreign Key (FK) là thước đo của sự hoàn chỉnh. Nhưng trong môi
trường thực tế tại Kakao, physical FK lại là gánh nặng.

### Toàn vẹn dữ liệu không phải là "quy tắc" mà là "vị trí của trách nhiệm"

Zephy.r kể lại rằng bài học đầu tiên và quan trọng nhất là: *không dùng physical FK không có nghĩa là từ bỏ toàn vẹn dữ liệu.* Đó là sự lựa chọn về **mô hình vận hành** — ai chịu
trách nhiệm đảm bảo tính toàn vẹn? Nếu chuyển trách nhiệm đó lên Application, thì tầng ứng dụng phải có test và logic bù đủ mạnh.

**Soft Delete** cũng là một thay đổi tư duy lớn. Trong sách giáo khoa, xóa là xóa. Nhưng trong thực tế, việc giữ lại bản ghi với trường `deleted_at` không phải là thỏa hiệp — đó
là **chiến lược vận hành bắt buộc** để phục vụ audit trail và khả năng khôi phục.

![Minh họa soft delete và hard delete trong thực tế](/images/2026/07/kakao-new-krew-onboarding-2026-02.png)
*Ảnh: Kakao Tech — so sánh giữa xóa cứng và xóa mềm, soft delete là chiến lược vận hành tiêu chuẩn tại Kakao*

### Index và SQL: từ "viết" sang "dẫn hướng"

Trước đây, các tân binh nghĩ về index đơn giản là "B-Tree giúp truy vấn nhanh hơn." Sau khóa học, họ bắt đầu nhìn index như một **quyết định cấu trúc dựa trên đặc tính dữ liệu**.
GIN, GiST, SP-GiST, Vector index — mỗi loại là một câu trả lời cho câu hỏi "database đang nhận những loại truy vấn nào?"

SQL cũng không còn đơn thuần là viết câu lệnh cho ra kết quả đúng. Khi bắt đầu đọc execution plan, một câu SQL có thể được hiểu theo những cách hoàn toàn khác nhau. Một số truy
vấn chạy qua index, số khác quét toàn bộ bảng — sự khác biệt đó thể hiện trực tiếp qua disk I/O và thời gian phản hồi.

> "Bây giờ tôi không còn 'viết' SQL nữa. Tôi 'dẫn hướng' đường chạy cho nó."

![Execution plan và cách đọc](/images/2026/07/kakao-new-krew-onboarding-2026-03.png)
*Ảnh: Kakao Tech — execution plan giúp lập trình viên hiểu cách database thực sự xử lý truy vấn*

### "Duplicate là ác" → "Duplicate là chiến lược"

Một trong những điểm khiến các tân binh thay đổi suy nghĩ nhiều nhất là quan điểm về dữ liệu trùng lặp. Khi còn đi học, chuẩn hóa là đức hạnh và JOIN là điều hiển nhiên. Nhưng khi
traffic và dữ liệu lớn dần, JOIN trở thành bottleneck.

**Denormalization có chủ đích** — cố tình lưu dữ liệu trùng lặp để tối ưu tốc độ đọc — không phải là thỏa hiệp mà là chiến lược. Mint.pearl chia sẻ rằng trong quá trình học về
MongoDB, điều này càng trở nên rõ ràng: chỉ khai báo quan hệ bằng `ref` thì ban đầu rất gọn, nhưng khi yêu cầu hiển thị phức tạp hơn, việc lưu sẵn thông tin dưới dạng snapshot
giúp render giao diện mà không cần thêm truy vấn.

### Hệ sinh thái dữ liệu: mỗi DBMS có một triết lý

Tân binh được học về kiến trúc High Availability (HA) của MySQL, cấu trúc PK của PostgreSQL, và các database cloud-native như Neon nơi tầng storage và compute được tách rời. Qua
đó, họ nhận ra rằng mỗi DBMS là một hệ thống phản ánh **triết lý riêng và sự đánh đổi (trade-off) giữa hiệu năng, nhất quán và khả năng mở rộng**.

Big Data cũng không còn là những cái tên riêng lẻ như Hadoop hay Spark, mà là một dòng chảy khổng lồ từ lưu trữ → quản lý → xử lý → phân tích.

![Hệ sinh thái cơ sở dữ liệu và big data](/images/2026/07/kakao-new-krew-onboarding-2026-04.jpg)
*Ảnh: Kakao Tech — tổng quan về hệ sinh thái dữ liệu mà tân binh được tiếp cận*

> "Thiết kế hoàn hảo trên lý thuyết không bằng thiết kế có thể chịu được thay đổi và kiểm soát được chi phí vận hành."

## Security & IT: Từ "chuyện của người khác" thành "giá trị mặc định của tôi"

Phần bảo mật bắt đầu bằng một câu hỏi nặng ký: *"Nếu dịch vụ của chúng ta bị rò rỉ thông tin cá nhân thì sao?"* Khoảnh khắc đó, bảo mật không còn là quy định hay việc của riêng
đội hạ tầng — nó trở thành **hệ quả bắt đầu từ code của chính mình**.

![Bảo mật là giá trị mặc định](/images/2026/07/kakao-new-krew-onboarding-2026-05.jpg)
*Ảnh: Kakao Tech — bảo mật phải được tích hợp ngay từ đầu, không phải thêm vào sau*

### CERT: Phân biệt còn khó hơn ngăn chặn

Một trong những bài học thực tế nhất đến từ DDoS. Các tân binh nhận ra rằng: tấn công đến 24/7 từ vô số địa chỉ khác nhau, và người phòng thủ luôn ở thế bị động. Nhưng khó nhất
không phải là chặn — mà là **phân biệt** đâu là traffic do sự kiện đột biến (một tin vui, một chương trình khuyến mãi) và đâu là tấn công thực sự.

Giải pháp cấp độ cá nhân mà họ mang về: trang bị Rate Limit, và quan trọng hơn — khi thấy dấu hiệu bất thường, đừng tự xử lý một mình mà hãy chia sẻ và kết nối với hệ thống ứng phó.

### API Security: "Tự hack chính mình"

Buổi thực hành API security là session sôi động nhất, theo lời kể của các tác giả. Lý do đơn giản: họ được trực tiếp khai thác lỗ hổng, đứng ở góc nhìn của kẻ tấn công.

> "Tự hack thấy vui. Nhưng nghĩ đến code mình bị hack thì… buồn lắm."

Chính cảm xúc đó là bước ngoặt. Bảo mật không còn là câu chuyện của dịch vụ nào đó xa xôi — nó là câu chuyện về code của chính mình.

### Bảo mật không phải "làm một lần rồi thôi"

Một số tân binh sau khóa học đã bắt đầu tự tìm hiểu về các lỗ hổng bảo mật mới nhất. Họ nghiên cứu xu hướng AI tìm điểm yếu, nhận ra rằng "khiên cũng thông minh và kiếm cũng thông
minh." Những kỹ thuật tấn công tâm lý — như QR code, quyền ứng dụng — cũng được đề cập, nhấn mạnh rằng bảo mật không chỉ là công nghệ mà còn là thói quen ở cấp độ sinh hoạt.

Kết luận: **bảo mật không phải bước kiểm tra cuối cùng — nó phải là giá trị mặc định gắn liền với quy trình phát triển ngay từ đầu.**

### Cuối cùng, software chạy trên "con người"

Một insight đơn giản nhưng sâu sắc: dù chúng ta quen nói chuyện với máy tính, kỹ thuật phần mềm rốt cuộc là giải quyết vấn đề của con người và làm việc cùng con người. Viết code
để người khác đọc được, để người đến sau có thể onboard ngay lập tức — đó mới là **chất lượng thực sự**.

> "Bảo mật không còn là cái khiên chặn ở cuối — nó đã trở thành giá trị mặc định trong phát triển. Và công nghệ, rốt cuộc, chạy trên con người, trên giao tiếp, trên chất lượng và
trên những quyết định đúng đắn."

## AI: Từ "nói chuyện với AI" sang "thiết kế và kết nối AI"

Ngày đầu tiên của phần AI, câu nói ám ảnh nhất mà các tân binh nghe được: **"Agent là design, không phải model."**

Trước khóa học, các kiến trúc AI Agent dường như là lĩnh vực không thể với tới. Nhưng khi nhìn vào ví dụ code, cấu trúc hóa ra không xa lạ: tính năng hay dùng được đóng thành
function (tool), luồng chính gọi theo điều kiện (routing), lỗi thì xử lý exception — chỉ khác là ở giữa có thêm một lời gọi LLM.

![Kiến trúc multi-agent](/images/2026/07/kakao-new-krew-onboarding-2026-06.png)
*Ảnh: Kakao Tech — thiết kế multi-agent dựa trên nguyên lý tương tự MSA*

### Kiểm soát xác suất bằng thiết kế hệ thống

LLM về bản chất là mô hình xác suất — kết quả có thể dao động mỗi lần. Điều Kakao muốn dạy các tân binh không phải là có được câu trả lời thông minh nhất trong một lần gọi, mà là
**tạo ra luồng xử lý ổn định và nhất quán**.

Các kỹ thuật được thực hành:
- **Prompt Chaining**: chia nhỏ yêu cầu thành nhiều bước để tránh nhiễu context
- **Few-shot**: dùng ví dụ để ép khuôn đầu ra
- **Routing**: rẽ nhánh prompt tùy theo điều kiện đầu vào

![Prompt chaining và routing](/images/2026/07/kakao-new-krew-onboarding-2026-07.png)
*Ảnh: Kakao Tech — kỹ thuật chia nhỏ và dẫn hướng prompt để kiểm soát đầu ra LLM*

### Multi-Agent và kết nối hệ thống: RAG, MCP

Thay vì phụ thuộc vào một AI monolithic duy nhất, kiến trúc **Multi-Agent** chia vai trò — phân tích dữ liệu, sinh nội dung, kiểm tra chất lượng — mỗi agent một nhiệm vụ. Điều này
gợi nhớ đến triết lý MSA (Microservices Architecture).

Điểm ấn tượng nhất với các tân binh là **MCP (Model Context Protocol)** và **RAG (Retrieval-Augmented Generation)**.

MCP cho phép hệ thống nội bộ của doanh nghiệp expose các function và dữ liệu dưới dạng Tool mà AI có thể gọi — một dạng "remote Function Calling" vượt qua giới hạn của LLM bằng
tài nguyên hệ thống thực tế. RAG giải quyết hallucination không phải bằng cách "cầu mong" AI nói đúng, mà bằng cách **chunk tài liệu, search vector tương đồng và augment kết quả**
— kiểm soát có cấu trúc.

![RAG và MCP architecture](/images/2026/07/kakao-new-krew-onboarding-2026-08.png)
*Ảnh: Kakao Tech — kiến trúc RAG kết hợp MCP giúp AI kết nối với dữ liệu doanh nghiệp*

### Từ "nổi giận" đến "yêu cầu rõ ràng"

Slide cuối cùng của phần AI có tựa đề khiến cả lớp bật cười vì… quá thật: **"La mắng LLM không giải quyết được gì."** Nhưng cười xong thì nhận ra đó là sự thật.

Trước khóa học, các tân binh có xu hướng *ném prompt, nhận kết quả tệ, và nổi giận.* Sau khóa học, quy trình thay đổi hoàn toàn: đặt mục tiêu → show format đầu ra bằng ví dụ →
dùng Sub-Agent → gắn dữ liệu RAG → quản lý context.

> "AI không phải là công nghệ để nhận được câu trả lời thông minh. AI là thiết kế để tạo ra hành vi thông minh."

## Kết luận: Bảo vệ an toàn, tạo ra giá trị

Nếu phải tóm gọn toàn bộ chương trình technical onboarding của Kakao trong một câu: **"Chuyển từ sinh viên đi tìm đáp án đúng sang kỹ sư cân bằng trọng lượng vận hành."**

40 New Krew không chỉ học được kỹ thuật — họ học được cách:
- Thiết kế database chịu được traffic thay vì chỉ đẹp trên sơ đồ
- Nghi ngờ code của chính mình về lỗ hổng bảo mật
- Kết nối AI với business logic một cách vững chắc

Nhưng trên tất cả, họ nhận ra rằng: không có đáp án duy nhất nào trong phát triển phần mềm. Điều làm nên một kỹ sư thực thụ là khả năng cân nhắc resource, bối cảnh, đưa ra lựa
chọn hợp lý nhất — và quan trọng không kém — **chia sẻ và thuyết phục đồng đội về quyết định đó.**

> "Không có đáp án đúng duy nhất trong phát triển và tăng trưởng. Điều quan trọng là cân nhắc resource và bối cảnh thực tế để đưa ra lựa chọn hợp lý nhất, và trình bày nó một cách
logic để thuyết phục đồng đội."

Những người viết bài — zephy.r, mint.pearl, theo.cha và rowan.ko — đã gửi lời cảm ơn đến tất cả giảng viên, các Krew đồng khóa, và những người đã tổ chức chương trình: **LP,
Shirley, Ayla, Sky, Simon** và tất cả những người liên quan. Họ kết thúc bằng lời hứa: *"Hãy chờ xem chúng tôi — những Krew — lớn lên thành những kỹ sư bảo vệ dịch vụ Kakao an
toàn hơn và tạo ra giá trị lớn hơn."*

{{< article-footer >}}
source: "Kakao Tech — Blog kỹ thuật chính thức của Kakao"
source_url: "https://tech.kakao.com/posts/815"
copyright: >
  Một phần thông tin trong bài được tham khảo từ [Kakao Tech — Blog kỹ thuật chính thức
  của Kakao](https://tech.kakao.com/posts/815). Mọi thương hiệu, hình ảnh và tài liệu gốc
  thuộc quyền sở hữu của chủ sở hữu tương ứng. Bài viết trên KoreaWiki chỉ tổng hợp, biên
  tập và phân tích phục vụ độc giả — không thay thế thông cáo hay tài liệu chính thức.
external:
  - title: "tech.kakao.com"
    url: "https://tech.kakao.com/posts/815"
  - title: "tech.kakao.com"
    url: "https://tech.kakao.com/blog"
  - title: "developers.kakao.com"
    url: "https://developers.kakao.com"
internal:
  - title: "Hallyu 2.0: Văn hóa Hàn Quốc phát triển như thế nào từ xuất khẩu thị trường ngách sang thống trị toàn cầu"
    url: "en/feature/hallyu-20-korean-culture-global-wave/"
  - title: "Giọng Nói Phía Sau Màn Ảnh: Các diễn viên lồng tiếng Hàn Quốc trở thành ngôi sao toàn cầu như thế nào"
    url: "en/feature/korean-voice-actors-rise/"
{{< /article-footer >}}
