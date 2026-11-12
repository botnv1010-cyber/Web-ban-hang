# Phạm vi quản trị và bàn giao

Repository thực tế là website giải pháp số Viettel Đồng Nai, không phải một website chỉ bán gói di động. Có một trang khách `index.html`, các modal bảng giá/đăng ký và admin `admin.html`. Đã đọc các file HTML/CSS/JS, server Python, Vercel handler, dữ liệu 111 gói, scripts và tests. Không có trang tin tức, danh sách điểm giao dịch hay router/component framework riêng.

| Trang/phần hiện có | Nội dung/thao tác tĩnh | Admin đã nối | Cách đối chiếu |
|---|---|---|---|
| Header/menu | Nhãn và liên kết điều hướng | Nội dung website → HEADER | Sửa nhãn/link, tải lại, bấm menu |
| Banner đầu trang | 8 poster, link ảnh và thứ tự | Nội dung website → Banner; sửa ảnh/link, nhân bản, thứ tự, ẩn; tải ảnh tạo WebP 768/1920 | Tải ảnh, lưu; kiểm tra srcset và carousel trên điện thoại/máy tính |
| Địa chỉ chạy chữ | Địa chỉ viết cứng | Nội dung website → Địa chỉ | Sửa, tải lại, đối chiếu chữ chạy |
| Hero | Tiêu đề, thông điệp, ảnh và liên hệ | Nội dung website → tiêu đề giải pháp | Sửa từng trường, đối chiếu giao diện |
| Dải dịch vụ | Nội dung ticker | Nội dung website → Dải dịch vụ | Sửa và tải lại |
| Hệ sinh thái | Ảnh, mô tả, tên và liên kết 5 dịch vụ | Nội dung website → Hệ sinh thái | Sửa trường, tải lại và mở bảng giá |
| Bảng giá và thiết bị | 111 gói trong JSON và bản HTML cũ | Gói dịch vụ: thêm/sửa/xóa/ẩn, ↑ ↓ sắp xếp; mọi nút bảng giá dùng API chung | CRUD, kiểm tra giá/ẩn/thứ tự và chọn gói vào form |
| Khuyến mãi | Tiêu đề, poster, liên kết | Nội dung website → Khuyến mãi | Thay ảnh/link và tải lại |
| Video/tài nguyên | Tiêu đề, ảnh, URL video | Nội dung website → Video; URL YouTube embed | Đổi video, tải lại và phát |
| Tư vấn/liên hệ | Nội dung giới thiệu, ảnh, hotline | Nội dung website + Hotline toàn cục | Đổi hotline, tải lại, kiểm tra tel: |
| FAQ | Câu hỏi và textarea nháp chỉ lưu localStorage | Nội dung website → FAQ: câu hỏi/câu trả lời; bỏ bản nháp khách, chỉ đọc | Sửa câu trả lời, tải lại bằng trình duyệt khác |
| Footer | Một dòng viết cứng | Trường Footer riêng | Sửa, lưu, tải lại |
| Form tư vấn, form chọn gói | Chỉ gửi email tư vấn viên, mất yêu cầu nếu lỗi email | Lưu DB, trả mã, email khách, inbox và trạng thái | Đăng ký email hợp lệ, phone rỗng; xem inbox, đổi trạng thái |
| Admin | Có sẵn CRUD gói | Dùng lại CSS/form/table, thêm điều hướng nội dung và inbox | Kiểm tra đăng nhập, API 401, CSRF, đăng xuất |

Các trường nội dung dùng binding DOM theo thứ tự cố định của giao diện hiện có, không nhận HTML từ admin. Nhân bản tạo phần tử từ mẫu cùng loại; thứ tự áp dụng cho phần tử cùng cha. Khi thay cấu trúc HTML trong một nhiệm vụ lập trình sau này phải di trú binding trong `data/content.json`; không tự ghi đè nội dung đã được admin sửa. Với banner nên nhân bản trường ảnh; với FAQ nhân bản câu hỏi (kèm câu trả lời). Nhãn kỹ thuật như nút lưu, thông báo lỗi, label biểu mẫu vẫn thuộc mã giao diện, không phải nội dung marketing.

## Cấu hình Vercel và Neon

1. Tạo Neon project và branch riêng cho Preview, lấy connection string có `sslmode=require`. Không dùng branch Production cho Preview. Tạo Vercel Blob store và kết nối project; dùng public Blob store cho banner công khai.
2. Tại Vercel → Settings → Environment Variables, đặt các tên trong `.env.example` cho **Preview**: `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` (ít nhất 12 ký tự), `BLOB_READ_WRITE_TOKEN`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (địa chỉ thuộc domain đã xác minh trong Resend). Không đưa giá trị vào Git, trình duyệt, NEXT_PUBLIC hay VITE variables. Vercel tự cấp Blob token khi liên kết store; dùng token của store Preview riêng.
3. Python 3.12+, cài `python3 -m pip install -r requirements.txt`. Khi DATABASE_URL đã được nạp an toàn vào process, chạy `python3 scripts/init_neon.py`. Lệnh tạo bảng và INSERT ON CONFLICT DO NOTHING, bảo toàn dữ liệu sửa. Handler cũng khởi tạo idempotent ở lần chạy đầu tiên.
4. Framework Other; build `python3 scripts/build_static.py`, output `public`; dùng `vercel.json`. Backend bundle gồm server/mailer/cms và data/*.json. Sau khi đổi biến môi trường phải redeploy.
5. Tạo nhánh Git riêng, import repository vào Vercel, deploy nhánh đó thành Preview. Vào **Deployment Protection**, bật Vercel Authentication cho Preview; nếu gói hỗ trợ có thể dùng Password Protection. Kiểm tra cửa sổ ẩn danh bị chặn trước khi chia sẻ URL Preview. Không đưa mật khẩu admin hay protection bypass token vào URL/changelog. Bảo vệ Preview là lớp riêng, không thay thế đăng nhập admin.
6. Mở `/admin` → đăng nhập. Sau khi lưu mỗi mục ở bảng trên, mở lại trang khách để so sánh. Chỉ publish production sau khi hoàn tất kiểm tra dịch vụ thật. `/admin.html` là shell đăng nhập công khai, dữ liệu inbox và mọi thao tác ghi được kiểm tra session/CSRF phía máy chủ; `/admin` chuyển người chưa đăng nhập về shell này.

## Email và dữ liệu khách hàng

Form giữ yêu cầu sau mọi kết quả gửi. `Chưa cấu hình email` khi thiếu khóa/địa chỉ gửi, `Gửi lỗi` khi timeout/provider từ chối, `Đã gửi` chỉ khi provider trả ID; ID lưu trong inbox. `Đã gửi` không đảm bảo thư đến inbox. Email gửi **đến khách**, chứa mã yêu cầu, thông tin gói lấy từ database và hotline hiện tại. Số điện thoại tùy chọn. Giới hạn 5 lần hợp lệ/IP/5 phút và idempotency theo requestId. Không tự động gửi lại email từ inbox; retry cùng mã không tạo yêu cầu/email trùng. Các yêu cầu trong admin giới hạn 500 mục mới nhất. Cần chính sách lưu giữ/xóa và sao lưu dữ liệu khách phù hợp khi vận hành.

## Kiểm chứng

- Bộ unittest: xác thực, CRUD/xung đột/cache gói; email với provider giả lập, kiểm tra email khách, lỗi vẫn lưu; thiếu cấu hình; phone tùy chọn; idempotency; seed chạy lại bảo toàn nội dung; tạo 2 ảnh WebP và upload giả lập.
- Chromium cục bộ: lưu và tải lại trường nội dung của cả 9 mục có nội dung chữ, kiểm tra binding ảnh responsive; đăng nhập qua `/admin`; sửa hotline/footer, tải lại khách thấy dữ liệu mới; API inbox chưa đăng nhập trả 401; gửi yêu cầu không có phone; xem inbox và đổi trạng thái.
- Kiểm tra cú pháp Python/JS và build tĩnh.
- **Chưa xác thực dịch vụ thật**: không có DATABASE_URL/Blob token/Resend key trong môi trường này. Chưa chạy migration trên Neon, upload Blob thật, nhận email thật hoặc dựng Vercel Preview có protection. Cần hoàn tất các bước cấu hình trên rồi kiểm tra lại toàn bộ bảng, đặc biệt carousel WebP và video trên thiết bị thật. Không khẳng định các mục chưa thử là đã đạt.


## Admin theo từng trang và cập nhật cache

- `/admin` chuyển đến `/admin/plans` sau đăng nhập. Mỗi mục có URL riêng: `/admin/plans`, `/admin/settings`, `/admin/consultations`, `/admin/content/section-0` … `/admin/content/section-9`. Mở trực tiếp/tải lại vẫn yêu cầu session; HTML là shell đăng nhập, API dữ liệu riêng kiểm tra quyền trên máy chủ.
- Desktop có sidebar; điện thoại có danh sách chọn trang. Nội dung là các thẻ thu gọn, có tìm kiếm, xem trước ảnh và thanh Lưu cố định. Banner gộp ảnh và liên kết trong một thẻ. Cảnh báo khi rời trang còn thay đổi chưa lưu.
- Mỗi lần API lưu thành công (gói, nội dung, trạng thái yêu cầu) gửi thông báo BroadcastChannel/localStorage theo loại dữ liệu. Không thông báo cho upload chưa áp dụng hoặc lưu thất bại. Gói bị xóa cache localStorage ngay cả khi chưa có tab khách mở. Nội dung chỉ áp dụng lại các section có dữ liệu khác, tránh tải lại ảnh/video không đổi. Ảnh upload được lưu bằng URL mới, không ghi đè ảnh đã cache.
- Trình duyệt khác thăm dò `/api/revisions` mỗi **5 giây khi trang hiển thị** và khi quay lại tab; chỉ tải danh mục/nội dung khi phiên bản đổi. Đây là cơ chế phát hiện định kỳ, không phải push giữa thiết bị. Nếu mất mạng/tab bị treo thì dữ liệu cập nhật sau khi kết nối/hoạt động lại. API revisions và dữ liệu nội dung không lưu cache; API gói xác thực ETag trước khi tái sử dụng. Không cache dữ liệu riêng của inbox.
- Lưu nhiều mục ở hai phiên đồng thời vẫn kiểm tra version, trả 409 cho bản sửa cũ thay vì ghi đè dữ liệu mới.

Kiểm chứng bổ sung: **15 unittest đạt**; Chromium kiểm tra mở/tải lại các URL admin, cập nhật nội dung ở cùng browser và context độc lập, làm mới bảng giá đang mở, tự lưu banner (Blob giả lập), responsive và đăng xuất. Có thể chạy lại browser test với Playwright + Chromium đã cài: `PYTHON=python3 CHROMIUM_PATH=/usr/bin/chromium node tests/admin_browser.cjs`. Bài test tự tạo mật khẩu, database tạm và server ở port rảnh, không dùng database Production. Dịch vụ Neon/Blob/Resend thật và cấu hình Vercel Production vẫn cần kiểm tra ở môi trường triển khai.


### Giữ phiên khi chuyển trang admin

Sidebar và bộ chọn trang dùng History API để chuyển nội dung giữa các URL riêng, giữ nguyên tài liệu và CSRF trong phiên. Mở URL trực tiếp hoặc tải lại vẫn gọi `/api/session`; chỉ hiện form đăng nhập sau HTTP 401. Trong thời gian kiểm tra, hiển thị trạng thái chờ; lỗi mạng/503 có nút Thử lại, không giả định rằng phiên đã hết hạn. Cookie HttpOnly vẫn do máy chủ kiểm tra trên mọi API riêng; không lưu token đăng nhập vào localStorage. Browser regression test có kiểm tra giữ nguyên document khi bấm sidebar, phục hồi session chậm và lỗi backend tạm thời.


## Quản lý nhóm dịch vụ

Trang `/admin/groups` có trong sidebar: thêm nhóm, sửa tên/mô tả, sắp xếp, bật/tắt và xóa nhóm chưa có gói. Mã nhóm tự tạo, cố định sau khi tạo. Danh sách có tìm kiếm theo tên/mã/mô tả, lọc trạng thái và số gói bật/tắt trong từng nhóm. Bấm **Thêm nhóm dịch vụ** hoặc **Sửa** để mở hộp thoại; bấm **Lưu nhóm** áp dụng ngay. Các thao tác ẩn/hiện, đổi thứ tự và xóa cũng lưu trực tiếp, không cần nút lưu chung. Muốn xóa nhóm đang có gói, chuyển hoặc xóa các gói trước; có thể ẩn nhóm để ngừng hiển thị mà giữ dữ liệu.

Nhóm lưu trong bảng `service_groups` trên cùng database Neon/SQLite; sáu nhóm hiện có được khởi tạo một lần, không ghi đè chỉnh sửa. `server.initialize()` và `scripts/init_neon.py` tự tạo bảng này, không cần biến môi trường mới. Khi lưu nhóm, phiên bản catalog tăng trong cùng transaction để vô hiệu hóa cache và kiểm tra xung đột ở form gói đang mở. API `/api/groups` cho phép đọc nhóm; thao tác ghi bắt buộc session và CSRF. Hai thao tác gán gói/xóa nhóm được tuần tự hóa bằng khóa row database để tránh liên kết bị mất.

Dropdown trong quản lý gói và bảng giá dùng nhóm thật. Nhóm mới có thẻ trong hệ sinh thái, tên/mô tả và nút mở bảng giá; nhóm cũ giữ thiết kế thẻ hiện có. Ẩn nhóm ẩn thẻ và các gói trong bảng giá; backend cũng từ chối đăng ký gói thuộc nhóm đã ẩn. Giới hạn tối đa 50 nhóm.

## Ảnh nguồn dưới 10 MB và ảnh xem trước

Admin nhận PNG/JPEG/WebP có dung lượng **dưới 10 MiB** (10 × 1024 × 1024 byte). Ảnh nguồn được đọc và tối ưu trong trình duyệt thành WebP trước khi gửi; payload ảnh tối đa khoảng 2.3 MB để nằm trong giới hạn request của Vercel. Backend kiểm tra ảnh rồi tạo hai bản WebP mobile/desktop lưu Blob như trước. Không tăng payload base64 lên 10 MB vì request sẽ vượt giới hạn Vercel. Không cần cấu hình thêm.

Ảnh `assets/...` trong admin được quy về gốc origin, tránh bị tìm nhầm ở `/admin/content/assets/...`. Preview có thông báo riêng nếu đường dẫn không đọc được. Banner liên kết trực tiếp ảnh cũng cập nhật đích ảnh khi thay nguồn, còn liên kết tùy chỉnh được giữ lại.

Browser test đã kiểm tra nhóm mới → gán gói → chọn gói vào form → ẩn nhóm; preview ảnh thật ở URL admin lồng nhau, file nguồn trên 2 MB tối ưu thành công, giới hạn 10 MB và cache. Blob/Resend trong browser test được giả lập; các kiểm tra database cục bộ dùng SQLite tách biệt. Cần đối chiếu dịch vụ thật sau Vercel deploy.


### Hoàn thiện thao tác quản lý nhóm

Trang nhóm có các thẻ tổng số/đang hiển thị/đang ẩn; bảng trên desktop và danh sách trên điện thoại. Mã nhóm có thể đặt khi tạo và cố định khi sửa. Hộp thoại có kiểm tra trường bắt buộc, mã trùng, độ dài và cảnh báo bỏ thay đổi chưa lưu. Lỗi API/xung đột giữ lại nội dung đang sửa; chỉ cập nhật danh sách và cache sau khi máy chủ lưu thành công.

Mỗi nhóm hiển thị tổng số gói, số gói bật/tắt và trạng thái ẩn theo nhóm. **Xem gói** mở `/admin/plans?group=<id>` với bộ lọc tương ứng; thêm gói tại đó tự chọn nhóm này. Bộ lọc được giữ khi tải lại trang. Bấm menu Gói dịch vụ sẽ quay về danh sách không lọc. Nút Xóa bị vô hiệu hóa cho nhóm đang có gói hoặc nhóm cuối cùng; backend vẫn kiểm tra liên kết khi lưu để xử lý trường hợp dữ liệu thay đổi từ phiên khác.

Kiểm thử Chromium bổ sung: tìm kiếm, sửa và giữ cố định mã nhóm, lên/xuống thứ tự, thêm/xóa nhóm trống, khóa xóa nhóm đã có gói, liên kết tới danh sách gói đã lọc, tự điền nhóm khi thêm gói, ẩn nhóm và responsive. Không bổ sung nhóm cha/con hay ảnh nhóm trong đợt này theo lựa chọn hoàn thiện thao tác hiện tại. Không cần cấu hình dịch vụ hoặc migration mới.
