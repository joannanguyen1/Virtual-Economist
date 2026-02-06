interface Responses {
    general: { [key: string]: string }; // Allow string-based indexing
    macroeconomic_indicators: { [key: string]: string };
    trends_and_predictions: { [key: string]: string };
    federal_reserve_policy: { [key: string]: string };
    sector_insights: { [key: string]: string };
    regional_data: { [key: string]: string };
    custom_calculations: { [key: string]: string };
  }
  
  declare const responses: { responses: Responses };
  export default responses;
  
