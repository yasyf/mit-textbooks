scheduler.xy.nav_height=0;
scheduler.config.hour_date="%h:%i";
scheduler.templates.week_scale_date = function(date){
    var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    return days[date.getDay()]
};
scheduler.ignore_week = function(date){
    if (date.getDay() == 6 || date.getDay() == 0){
        return true;
    }
};
$("#scheduler").dhx_scheduler({
    mode: "week",
    readonly: true,
    first_hour: 8,
    last_hour: 20,
});