const { RoninAgent } = require('./dist/core/Agent.js');
(async () => {
    console.log("Creating agent...");
    const agent = new RoninAgent();
    console.log("Initializing agent...");
    await agent.init();
    console.log("Init complete. Linked VM:", agent.linkedVm);
})();
