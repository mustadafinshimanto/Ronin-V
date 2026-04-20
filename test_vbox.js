const { VBoxExecutor } = require('./dist/executors/Executors.js');
(async () => {
    const vbox = new VBoxExecutor();
    const vms = await vbox.listVMs();
    console.log("Found VMs:", vms);
    if (vms.length > 0) {
        console.log("Testing connection...");
        const result = await vbox.testConnection(vms[0].name, "kali", "kali");
        console.log("Connection result:", result);
    }
})();
