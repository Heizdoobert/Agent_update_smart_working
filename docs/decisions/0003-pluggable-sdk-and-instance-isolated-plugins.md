# ADR-003: Kiến trúc Pluggable SDK, Cô lập Instance và Onboarding Wizard

## Status
Accepted

## Date
2026-10-29

## Context
Người dùng muốn áp dụng `agent_system` vào các repo dự án cụ thể (như game bot, automation testing, web pipeline) mà không phải sửa mã nguồn lõi. Mỗi dự án cần:
1. Đăng ký các Action nghiệp vụ tùy biến (Domain Actions).
2. Đăng ký các bộ kiểm tra Critic riêng (Domain Critics).
3. Tiêm bộ luật vận hành prompt của dự án (`.agent/rules.md`).
4. Khởi tạo nhanh chóng thông qua tương tác hỏi - đáp (Interactive Onboarding Wizard).

Các rủi ro nghiêm trọng được phát hiện trong quá trình Adversarial Review (Doubt-Driven Development):
- **Thực thi mã tùy ý (ACE) & Module Shadowing:** Nếu quét nạp động tại CWD mà không có whitelist hoặc thêm CWD vào `sys.path`.
- **Nhiễm chéo trạng thái đồng thời (Concurrency State Contamination):** Nếu registry sử dụng singleton toàn cục để mutate `CriticEngine` hoặc `TransitionModel`.
- **Treo lệnh tự động / CI:** Nếu wizard tự động kích hoạt ngầm ở mọi câu lệnh CLI trong terminal TTY.

## Decision
Xây dựng module [`agent_system.sdk`](file:///mnt/second_drive/Agent_system/agent_system/sdk/):
1. **Giao thức chuẩn `BasePlugin` & `PluginManifest`:** Các plugin kế thừa từ [`BasePlugin`](file:///mnt/second_drive/Agent_system/agent_system/sdk/contracts.py) và cung cấp các hook lifecycle (`on_load`, `on_unload`), event hooks (`on_before_plan`, `on_after_plan`, `on_critic_report`), actions (`get_actions()`) và critics (`get_critics() -> List[CriticProtocol]`).
2. **Cô lập theo Instance (Instance-based Registry):** [`PluginRegistry`](file:///mnt/second_drive/Agent_system/agent_system/sdk/registry.py) quản lý plugin theo từng instance độc lập, không dùng mutable state toàn cục. Hỗ trợ cơ chế đa plugin với phân xử độ ưu tiên (`priority`).
3. **Nạp động an toàn (Safe Dynamic Loader):** Sử dụng `importlib.util.spec_from_file_location` với kiểm tra Path Whitelisting nghiêm ngặt; tuyệt đối không thêm CWD vào `sys.path`.
4. **Onboarding Wizard an toàn (Priority 1):** [`OnboardingWizard`](file:///mnt/second_drive/Agent_system/agent_system/sdk/wizard.py) chỉ chạy khi người dùng gọi `agent-system init` hoặc chạy lệnh gốc `agent-system` trong TTY; không bao giờ chặn các lệnh con tiêu chuẩn (`critic`, `plan`, `session`, `memory`, `skill`) hay khi chạy qua UNIX pipe. Hỗ trợ rollback dọn dẹp sạch sẽ nếu bị ngắt I/O (`KeyboardInterrupt`).

## Alternatives Considered

### 1. Hardcode các adapter trong repo lõi
- **Ưu điểm:** Dễ viết, không cần thiết kế cơ chế dynamic load.
- **Nhược điểm:** Phá vỡ tính domain-agnostic, repo phình to với mã nguồn của hàng chục dự án khác nhau.
- **Lý do bác bỏ:** Vi phạm ADR-001.

### 2. Sử dụng Singleton Registry toàn cục
- **Ưu điểm:** Có thể truy cập plugin từ bất kỳ đâu không cần truyền instance.
- **Nhược điểm:** Dẫn đến race condition và xung đột state khi nhiều phiên agent hoặc subagent chạy song song trên cùng một tiến trình Python.
- **Lý do bác bỏ:** Không đáp ứng yêu cầu an toàn đồng thời (Contract 5).

## Consequences
- Bất kỳ dự án ngoài nào cũng có thể cắm (plug-in) và tháo (plug-out) logic riêng bằng 1 lệnh `agent-system init`.
- Đảm bảo an toàn tuyệt đối chống ACE, module shadowing và race condition.
