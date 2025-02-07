const express = require("express");
const bodyParser = require("body-parser");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { Pool } = require("pg");
const cors = require("cors");

const app = express();
const pool = new Pool({
  user: "postgres",
  host: "localhost",
  database: "ayurvedic_db",
  password: "changeme",
  port: 5432,
});

app.use(cors());
app.use(bodyParser.json());

const secretKey = "your_secret_key";

// Signup route
app.post("/signup", async (req, res) => {
  const { name, email, password } = req.body;
  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    const result = await pool.query(
      "INSERT INTO users (name, email, password) VALUES ($1, $2, $3) RETURNING *",
      [name, email, hashedPassword]
    );
    res
      .status(201)
      .json({ message: "User registered successfully", user: result.rows[0] });
  } catch (error) {
    console.error(error);
    if (error.code === "23505") {
      res.status(400).json({ message: "Email already exists" });
    } else {
      res.status(500).json({ message: "Internal server error" });
    }
  }
});

// Login route
app.post("/login", async (req, res) => {
  const { email, password } = req.body;
  try {
    const result = await pool.query("SELECT * FROM users WHERE email = $1", [
      email,
    ]);
    const user = result.rows[0];
    if (user && (await bcrypt.compare(password, user.password))) {
      const token = jwt.sign({ id: user.id }, secretKey, { expiresIn: "1h" });
      res.status(200).json({ message: "Login successful", token });
    } else {
      res.status(400).json({ message: "Invalid email or password" });
    }
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Internal server error" });
  }
});

// Middleware to authenticate token
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];
  if (!token) return res.status(401).json({ message: "Access token missing" });

  jwt.verify(token, secretKey, (err, user) => {
    if (err) return res.status(403).json({ message: "Invalid token" });
    req.user = user;
    next();
  });
};

// Example protected route
app.get("/protected", authenticateToken, (req, res) => {
  res
    .status(200)
    .json({ message: "Protected route access granted", user: req.user });
});

const port = 3000;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
