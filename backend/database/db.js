import pkg from "pg";
import dotenv from "dotenv";
import {
  GetSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";

dotenv.config();

const { Pool } = pkg;

const DEFAULT_DB_SECRET_ID = "ards-password";

let cachedPassword = null;

async function resolveDbPassword() {
  if (cachedPassword) {
    return cachedPassword;
  }

  const secretArn = process.env.DB_SECRET_ARN || DEFAULT_DB_SECRET_ID;
  const region = process.env.AWS_REGION || "us-east-1";

  const client = new SecretsManagerClient({ region });
  const response = await client.send(
    new GetSecretValueCommand({ SecretId: secretArn }),
  );

  const secretString = response.SecretString;
  if (!secretString) {
    throw new Error("Secrets Manager returned an empty DB secret.");
  }

  const secret = JSON.parse(secretString);
  if (!secret.password) {
    throw new Error("DB secret does not contain a password field.");
  }

  cachedPassword = secret.password;
  return cachedPassword;
}

const password = await resolveDbPassword();

const pool = new Pool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password,
  database: process.env.DB_NAME,
  port: process.env.DB_PORT,
  ssl: { rejectUnauthorized: false },
});

export default pool;
