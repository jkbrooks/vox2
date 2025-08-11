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
}