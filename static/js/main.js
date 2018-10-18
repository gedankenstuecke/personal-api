$(function(){
    console.log($('#json_url').attr('href'));
    var json_url = $('#json_url').attr('href');
    $.get(json_url, function(data){
        console.log(data);
        if(data.location.tz){
          var local_time = new Date();
          local_time = new Date(local_time .getTime() + data.location.tz_offset);
          console.log(local_time);
          $("#local_time").html(local_time.getHours()+":"+local_time.getMinutes());
          $("#time_zone").html(data.location.tz);
          $("#time_info").removeClass('invisible');
        };

        if(data.location.place){
          $("#location_name").html(data.location.place);
          $("#location_info").removeClass('invisible');
        };

        if(data.location.weather){
          $("#weather_condition").html(data.location.weather.condition_text);
          $("#weather_temperature").html(data.location.weather.temperature_outside);
          $("#condition_icon").attr("class", "wi wi-yahoo-" + data.location.weather.code);
          $("#weather").removeClass('invisible');
        }

        if(data.activity){
          $("#heart_rate").html(data.activity.heart_rate);
          $("#steps").html(data.activity.steps);
          $("#sleep").html(data.activity.hours_slept);
          $("#battery_level").html(data.location.battery_level*100);
          $("#battery_state").html(data.location.battery_state);
          $("#activity_info").removeClass('invisible');
        };

        if(data.music){
          $("#title").html(data.music.title);
          $("#artist").html(data.music.artist);
          $("#music_info").removeClass('invisible');
        };

    });
});
