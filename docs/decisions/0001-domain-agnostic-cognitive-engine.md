# ADR-001: Xây dựng lõi nhận thức Domain-Agnostic độc lập thuần Python

## Status
Accepted

## Date
2026-10-28

## Context
Trước đây, các quy trình nhận thức (ToT/GoT DAG, $A^*$, MCTS, in-memory self-reflection) bị gắn chặt trực tiếp vào repo tự động hóa game (`Knit Away`), phụ thuộc sâu vào Airtest, Android ADB, Poco UI SDK và môi trường đồ họa. Khi cần tái sử dụng trí tuệ nhận thức cho các dự án khác (như web scraping, backend microservices, coding automation), kỹ sư phải sao chép mã nguồn và gỡ bỏ các dependency nặng nề một cách thủ công.

Yêu cầu cốt lõi:
- Lõi framework phải hoạt động hoàn toàn offline, 100% domain-agnostic.
- Không phụ thuộc bất kỳ thư viện bên ngoài nào ngoài Python standard library (Python 3.9+).
- Độ trễ cực thấp (sub-millisecond latency cho planning và AST audit).

## Decision
Tách toàn bộ các thuật toán nhận thức thành package độc lập [`agent_system`](file:///mnt/second_drive/Agent_system):
1. **Core Contracts:** Giao tiếp thông qua các dataclass và Abstract Protocol chuẩn ([`agent_system.core.contracts`](file:///mnt/second_drive/Agent_system/agent_system/core/contracts.py)).
2. **Reasoning:** Graph of Thoughts DAG ([`ThoughtGraph`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/graph.py)), $A^*$ Planner ([`AStarPlanner`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/astar.py)) và MCTS ([`MCTSPlanner`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/mcts.py)).
3. **Reflection:** [`CriticEngine`](file:///mnt/second_drive/Agent_system/agent_system/reflection/critic.py) phối hợp các adapter chuyên biệt như [`PythonAstCritic`](file:///mnt/second_drive/Agent_system/agent_system/reflection/adapters/python_ast.py).
4. Mọi logic đặc thù từng nghiệp vụ (Game, Web, Cloud) được chuyển giao hoàn toàn cho tầng Adapter và Plugin SDK bên ngoài.

## Alternatives Considered

### 1. Giữ nguyên mono-repo trong Knit
- **Ưu điểm:** Không cần tạo repo mới, tận dụng test suite có sẵn.
- **Nhược điểm:** Bị ô nhiễm bởi dependency Airtest/OpenCV/Poco, không thể đóng gói thành thư viện nhẹ dùng chung cho các AI Agent khác.
- **Lý do bác bỏ:** Vi phạm nguyên tắc Single Responsibility và tính di động của mã nguồn.

### 2. Sử dụng framework có sẵn như LangChain / AutoGen
- **Ưu điểm:** Hệ sinh thái lớn, nhiều tích hợp sẵn.
- **Nhược điểm:** Phụ thuộc nặng vào third-party packages (hàng trăm MB dependencies), yêu cầu external LLM API cho mọi bước suy luận, độ trễ cao (>1-2s), khó kiểm soát chặt chẽ ngân sách ngữ cảnh và an toàn bộ nhớ.
- **Lý do bác bỏ:** Không đáp ứng yêu cầu sub-millisecond, pure Python stdlib và zero external dependency.

## Consequences
- Hệ thống hoạt động siêu nhẹ, import tức thì (<20ms) và chạy 80+ tests trong dưới 0.6 giây.
- AI Agent trong bất kỳ workspace nào đều có thể sử dụng CLI `agent-system` hoặc `import agent_system`.
- Cần xây dựng tầng Plugin SDK để các dự án bên ngoài có thể cắm thêm domain actions và critics riêng.
