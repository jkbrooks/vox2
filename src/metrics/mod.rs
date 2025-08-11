pub enum MetricType {
    Counter,
    Gauge,
    Histogram,
    Timer,
}pub struct Metric {
    name: String,
    metric_type: MetricType,
    value: f64,
    timestamp: u64,
}impl Metric {
    pub fn new(name: String, metric_type: MetricType) -> Self {
        Metric {
            name,
            metric_type,
            value: 0.0,
            timestamp: 0,
        }
    }

    pub fn update_value(&mut self, value: f64) {
        self.value = value;
    }

    pub fn increment(&mut self) {
        self.value += 1.0;
    }

    pub fn get_value(&self) -> f64 {
        self.value
    }

    pub fn get_timestamp(&self) -> u64 {
        self.timestamp
    }
}