```text id="w5l4p9"
You are a senior backend engineer.

Help me build a production-style JWT authentication system for a TypeScript + Prisma + PostgreSQL backend.

IMPORTANT:
- Build incrementally and explain each step.
- Do NOT skip implementation details.
- Explain architecture decisions clearly.
- Use clean modular backend structure.
- Prefer scalable patterns over quick hacks.
- Include validation and security best practices.

==================================================
TECH STACK
==================================================

Backend:
- Node.js
- TypeScript

Database:
- PostgreSQL
- Prisma ORM

Authentication:
- JWT
- bcrypt


Environment:
- dotenv

==================================================
PROJECT STRUCTURE
==================================================

Use this structure:

src/
├── modules/
│   └── auth/
│       ├── auth.controller.ts
│       ├── auth.service.ts
│       ├── auth.routes.ts
│       ├── auth.schema.ts
│       └── auth.types.ts
│
├── plugins/
├── middleware/
├── utils/
├── types/
└── index.ts

==================================================
AUTHENTICATION FEATURES
==================================================

Implement:

1. User registration
2. User login
3. Password hashing using bcrypt
4. JWT access token generation
5. JWT verification middleware
6. Protected route example
7. Environment-based secret management
9. Proper error handling
10. Prisma integration

==================================================
DATABASE MODEL
==================================================

Prisma User model:

model User {
  id            String   @id @default(uuid())
  email         String   @unique
  passwordHash  String
  createdAt     DateTime @default(now())
}

==================================================
API REQUIREMENTS
==================================================

POST /auth/register
- email
- password

POST /auth/login
- email
- password

GET /me
- protected route
- returns authenticated user

==================================================
SECURITY REQUIREMENTS
==================================================

- Hash passwords using bcrypt
- Never return password hashes
- Validate all inputs
- Use JWT expiration
- Store secrets in .env
- Handle duplicate email registration
- Return proper HTTP status codes
- Use async/await everywhere
- Add centralized error handling where appropriate

==================================================
DELIVERABLE STYLE
==================================================

For EACH step:

2. Generate:
- exact code files
- installation commands
- Prisma schema updates

3. Include:
- example requests/responses

==================================================
STARTING POINT
==================================================


Start with:
1. installing required auth dependencies
3. auth module setup
```
