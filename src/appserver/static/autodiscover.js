
require.config({
    paths: {
        "app": "../app",
        "helpers/user_agent": "../app/alert_manager/contrib/stubs/user_agent",
        "views/shared/pcss/select2.pcss": "../app/alert_manager/contrib/stubs/select2_pcss",
        "select2/select2": "../app/alert_manager/contrib/select2/select2"
    }
});
require(['splunkjs/mvc/simplexml/ready!'], function(){
    require(['splunkjs/ready!'], function(){
        // The splunkjs/ready loader script will automatically instantiate all elements
        // declared in the dashboard's HTML.
    });
});