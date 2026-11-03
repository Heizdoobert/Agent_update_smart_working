# Intent: Long‑Term Memory for Agent

## Outcome
Tạo hệ thống lưu trữ ba tầng, mỗi task tạo **insight dạng JSON** (≤200 ký tự), nhúng và lưu vào **Milvus 2**. Khi Agent chạy vòng Reflexion trong các phiên làm việc tiếp theo, nó sẽ tự động truy vấn những insight này.

## User
Cùng một Agent thực thi Reflexion; không có các Agent hay dịch vụ bên ngoài truy cập dữ liệu.

## Why now
Cần cơ chế lưu trữ bền vững để tránh mất mát kiến thức và giảm thời gian lặp lại.

## Success
- Insight lưu dưới dạng JSON, metadata không chứa key bí mật.
- Truy vấn đáp ứng **≤ 50 ms**.
- Kết nối Milvus 2 localhost, không cần API key.

## Constraint
- Không ghi key vào metadata.
- Độ trễ ≤ 50 ms.
- Sử dụng Milvus 2 local.

## Out of scope
- Hỗ trợ multi‑node/cloud.
- Mã hoá metadata.
- Giao diện UI cho người dùng.
