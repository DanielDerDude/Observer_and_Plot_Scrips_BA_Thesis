#ifndef _INCLUDES_H_
#define _INCLUDES_H_
#include "../_components/includes.h"
#include "../_components/timing_functions.h"
#endif

static const char* TAG1 = "EDGE_DETECT";

typedef enum {
    RISING_EDGE,
    FALLING_EDGE,
} event_id_t;

typedef struct {
    event_id_t id;
    gpio_num_t gpio_num;
    int64_t timestamp;
} gpio_event_t;

static QueueHandle_t gpio_evt_queue = NULL;

// list of usable input pins
#define PIN_AMOUNT 7
static const gpio_num_t gpio_list[PIN_AMOUNT] = {18, 19, 21, 22, 23, 32, 33};

// isr for rising edges
static void IRAM_ATTR gpio_isr_handler(void* arg)
{
    int64_t time_now = get_systime_us();        // save timestamp
    gpio_num_t gpio_num = (gpio_num_t) arg;     // gpio that triggered the isr
    gpio_event_t evt;                           // create event for later handling
    
    if (gpio_get_level(gpio_num) == 1){         // check if rising edge or falling edge triggered the isr
        evt.id = RISING_EDGE;
    }else{
        evt.id = FALLING_EDGE;
    }
    evt.timestamp = time_now;                   // associate event with timestamp
    evt.gpio_num  = gpio_num;                   // associate event with gpio number

    xQueueSendFromISR(gpio_evt_queue, &evt, NULL);  // send event to queue
}

// task prints events on console
static void observer_task(void* arg)
{
    gpio_event_t evt;
    while (xQueueReceive(gpio_evt_queue, &evt, portMAX_DELAY) == pdTRUE) {     // get event from queue        
        
        if(evt.id == RISING_EDGE){
            printf("GPIO%d EDGE RISING  %lld \n", evt.gpio_num, evt.timestamp);
            fflush(stdout);  
        } 
        else{
            printf("GPIO%d EDGE FALLING %lld \n", evt.gpio_num, evt.timestamp);   
            fflush(stdout);
        }
    }
}

static void init(){
    // compute bit mask
    uint64_t bit_mask = 0; 
    for (uint8_t i = 0; i < PIN_AMOUNT; i++){
        bit_mask |= (1ULL << (uint64_t)gpio_list[i]);
    }
    // configure gpio setup
    gpio_config_t io_conf = {};                // zero init struct
    io_conf.intr_type = GPIO_INTR_ANYEDGE;      // interrupt of any edge
    io_conf.pin_bit_mask = bit_mask;            // bit mask of the pins
    io_conf.mode = GPIO_MODE_INPUT;             // set as input mode
    io_conf.pull_down_en = 1;                   // no pull down         need to be strapped low if not used  
    io_conf.pull_up_en = 0;                     // no pull up           the observed devices need to have pull down/up configured outputs
    ESP_ERROR_CHECK( gpio_config(&io_conf) );

    // install gpio isr service
    ESP_ERROR_CHECK( gpio_install_isr_service(ESP_INTR_FLAG_IRAM | ESP_INTR_FLAG_EDGE) ); // isr in IRAM for fast execution, shared isr for all pins and all edges
    
    // hook isr handler to all gpio pins in gpio_list
    for (uint8_t i = 0; i < PIN_AMOUNT; i++){
        ESP_ERROR_CHECK( gpio_isr_handler_add(gpio_list[i], gpio_isr_handler, (void*)gpio_list[i]) );
    }




    // create a queue to handle gpio event from isrs
    gpio_evt_queue = xQueueCreate(PIN_AMOUNT*3, sizeof(gpio_event_t));

    // start observer task
    xTaskCreate(observer_task, "observer_task", 2048, NULL, 10, NULL);
}

void app_main(void)
{
    init();
}
