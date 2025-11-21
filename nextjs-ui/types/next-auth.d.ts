import "next-auth";
import "next-auth/jwt";

/**
 * Type declarations for extending NextAuth Session and JWT types
 * Adds custom fields: accessToken, userId, tokenVersion
 */

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      role?: string;
    };
    accessToken: string;
    tokenVersion: number;
  }

  interface User {
    id: string;
    email?: string | null;
    name?: string | null;
    accessToken: string;
    tokenVersion: number;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string;
    userId: string;
    tokenVersion: number;
  }
}
