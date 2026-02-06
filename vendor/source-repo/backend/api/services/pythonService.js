// services/pythonService.js
const { spawn } = require("child_process");
const path = require("path");
const os = require("os");

const invokePython = (question, agentSelection = {}) => {
  return new Promise((resolve, reject) => {
    const pythonScriptPath = path.resolve(__dirname, "../../app/main.py");
    const pythonExecutable = os.platform() === "win32" ? "python" : "python3";
    const args = [
      pythonScriptPath,
      question,
      JSON.stringify(agentSelection),
    ];

    console.log("Spawning Python with arguments:", args);

    const pythonProcess = spawn(pythonExecutable, args);

    let output = "";
    let errorOutput = "";

    pythonProcess.stdout.on("data", (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    pythonProcess.on("close", (code) => {
      if (code === 0) {
        resolve(output.trim());
      } else {
        reject(errorOutput || "Error occurred in Python script");
      }
    });
  });
};

module.exports = { invokePython };
