import numpy as np
import pandas as pd
from typing import List, Dict, Any

class CMAAnalyzer:
    def __init__(self):
        pass
        
    def run_cma_analysis(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run Comparative Market Analysis on property data"""
        try:
            # For demo purposes, we'll use mock comparable sales data
            # In a real implementation, this would come from Relab API
            comparable_sales = self.get_mock_comparable_sales(property_data)
            
            if not comparable_sales:
                return {
                    'error': 'No comparable sales found',
                    'benchmarks': {},
                    'comparable_sales': []
                }
                
            # Calculate benchmarks
            benchmarks = self.calculate_benchmarks(comparable_sales, property_data)
            
            # Generate valuation range
            valuation_range = self.calculate_valuation_range(benchmarks, property_data)
            
            return {
                'comparable_sales': comparable_sales,
                'benchmarks': benchmarks,
                'valuation_range': valuation_range,
                'analysis_summary': self.generate_analysis_summary(benchmarks, valuation_range)
            }
            
        except Exception as e:
            print(f"Error running CMA analysis: {e}")
            return {'error': str(e)}
            
    def get_mock_comparable_sales(self, property_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get mock comparable sales data for demo purposes"""
        # This would normally come from Relab API
        # For demo, we'll generate realistic mock data based on the subject property
        
        base_price = property_data.get('cv', 800000)
        base_land_area = property_data.get('land_area', 600)
        base_floor_area = property_data.get('floor_area', 120)
        
        comparable_sales = []
        
        for i in range(8):  # Generate 8 comparable sales
            # Vary the sale price by ±15%
            price_variation = np.random.uniform(0.85, 1.15)
            sale_price = base_price * price_variation
            
            # Vary land area by ±20%
            land_variation = np.random.uniform(0.8, 1.2)
            land_area = base_land_area * land_variation
            
            # Vary floor area by ±20%
            floor_variation = np.random.uniform(0.8, 1.2)
            floor_area = base_floor_area * floor_variation
            
            # Generate CV (typically close to sale price)
            cv = sale_price * np.random.uniform(0.9, 1.1)
            
            comparable_sales.append({
                'address': f'Mock Address {i+1}',
                'sale_price': round(sale_price, 0),
                'cv': round(cv, 0),
                'land_area': round(land_area, 1),
                'floor_area': round(floor_area, 1),
                'sale_date': f'2024-{np.random.randint(1, 12):02d}-{np.random.randint(1, 28):02d}',
                'bedrooms': property_data.get('bedrooms', 3) + np.random.randint(-1, 2),
                'bathrooms': property_data.get('bathrooms', 2) + np.random.randint(-1, 2)
            })
            
        return comparable_sales
        
    def calculate_benchmarks(self, comparable_sales: List[Dict[str, Any]], property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate CMA benchmarks"""
        if not comparable_sales:
            return {}
            
        df = pd.DataFrame(comparable_sales)
        
        # Benchmark 1: Average sale/CV ratio
        sale_cv_ratios = df['sale_price'] / df['cv']
        avg_sale_cv_ratio = sale_cv_ratios.mean()
        
        # Benchmark 2: Average floor $/sqm rate
        floor_rates = df['sale_price'] / df['floor_area']
        avg_floor_rate = floor_rates.mean()
        
        # Benchmark 3: Average land $/sqm rate
        land_rates = df['sale_price'] / df['land_area']
        avg_land_rate = land_rates.mean()
        
        # Calculate standard deviations for confidence intervals
        sale_cv_std = sale_cv_ratios.std()
        floor_rate_std = floor_rates.std()
        land_rate_std = land_rates.std()
        
        return {
            'avg_sale_cv_ratio': round(avg_sale_cv_ratio, 3),
            'avg_floor_rate': round(avg_floor_rate, 0),
            'avg_land_rate': round(avg_land_rate, 0),
            'sale_cv_std': round(sale_cv_std, 3),
            'floor_rate_std': round(floor_rate_std, 0),
            'land_rate_std': round(land_rate_std, 0),
            'num_comparables': len(comparable_sales)
        }
        
    def calculate_valuation_range(self, benchmarks: Dict[str, Any], property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate valuation range based on benchmarks"""
        if not benchmarks:
            return {}
            
        cv = property_data.get('cv', 800000)
        land_area = property_data.get('land_area', 600)
        floor_area = property_data.get('floor_area', 120)
        
        # Valuation using sale/CV ratio
        sale_cv_valuation = cv * benchmarks['avg_sale_cv_ratio']
        sale_cv_range = {
            'low': sale_cv_valuation * (1 - benchmarks['sale_cv_std']),
            'high': sale_cv_valuation * (1 + benchmarks['sale_cv_std'])
        }
        
        # Valuation using floor rate
        floor_valuation = floor_area * benchmarks['avg_floor_rate']
        floor_range = {
            'low': floor_valuation * (1 - benchmarks['floor_rate_std'] / benchmarks['avg_floor_rate']),
            'high': floor_valuation * (1 + benchmarks['floor_rate_std'] / benchmarks['avg_floor_rate'])
        }
        
        # Valuation using land rate
        land_valuation = land_area * benchmarks['avg_land_rate']
        land_range = {
            'low': land_valuation * (1 - benchmarks['land_rate_std'] / benchmarks['avg_land_rate']),
            'high': land_valuation * (1 + benchmarks['land_rate_std'] / benchmarks['avg_land_rate'])
        }
        
        # Calculate overall range
        all_valuations = [
            sale_cv_range['low'], sale_cv_range['high'],
            floor_range['low'], floor_range['high'],
            land_range['low'], land_range['high']
        ]
        
        overall_range = {
            'low': round(min(all_valuations), 0),
            'high': round(max(all_valuations), 0),
            'mid': round(np.mean(all_valuations), 0)
        }
        
        return {
            'sale_cv_method': {
                'value': round(sale_cv_valuation, 0),
                'range': {k: round(v, 0) for k, v in sale_cv_range.items()}
            },
            'floor_rate_method': {
                'value': round(floor_valuation, 0),
                'range': {k: round(v, 0) for k, v in floor_range.items()}
            },
            'land_rate_method': {
                'value': round(land_valuation, 0),
                'range': {k: round(v, 0) for k, v in land_range.items()}
            },
            'overall_range': overall_range
        }
        
    def generate_analysis_summary(self, benchmarks: Dict[str, Any], valuation_range: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis summary"""
        overall_range = valuation_range.get('overall_range', {})
        
        # Calculate confidence level based on number of comparables
        num_comparables = benchmarks.get('num_comparables', 0)
        if num_comparables >= 8:
            confidence = 'High'
        elif num_comparables >= 5:
            confidence = 'Medium'
        else:
            confidence = 'Low'
            
        # Calculate range width as percentage
        range_width = ((overall_range.get('high', 0) - overall_range.get('low', 0)) / overall_range.get('mid', 1)) * 100
        
        if range_width < 15:
            market_volatility = 'Low'
        elif range_width < 25:
            market_volatility = 'Medium'
        else:
            market_volatility = 'High'
            
        return {
            'confidence_level': confidence,
            'market_volatility': market_volatility,
            'valuation_range_width': round(range_width, 1),
            'recommendation': self.generate_recommendation(confidence, market_volatility, overall_range),
            'key_insights': [
                f"Based on {num_comparables} comparable sales",
                f"Valuation range: ${overall_range.get('low', 0):,.0f} - ${overall_range.get('high', 0):,.0f}",
                f"Mid-point estimate: ${overall_range.get('mid', 0):,.0f}",
                f"Market confidence: {confidence}",
                f"Market volatility: {market_volatility}"
            ]
        }
        
    def generate_recommendation(self, confidence: str, volatility: str, valuation_range: Dict[str, Any]) -> str:
        """Generate investment recommendation"""
        mid_value = valuation_range.get('mid', 0)
        
        if confidence == 'High' and volatility == 'Low':
            return f"Strong market data supports a valuation around ${mid_value:,.0f}. Consider this property for investment."
        elif confidence == 'High' and volatility == 'Medium':
            return f"Good market data available. Valuation range suggests ${mid_value:,.0f} ± 10%. Monitor market conditions."
        elif confidence == 'Medium':
            return f"Moderate market data. Valuation around ${mid_value:,.0f} with higher uncertainty. Additional research recommended."
        else:
            return f"Limited market data available. Valuation estimate ${mid_value:,.0f} has high uncertainty. Extensive due diligence required."
            
    def adjust_criteria(self, comparable_sales: List[Dict[str, Any]], target_count: int = 8) -> Dict[str, Any]:
        """Adjust CMA criteria to get target number of comparables"""
        current_count = len(comparable_sales)
        
        if current_count == target_count:
            return {'status': 'optimal', 'message': f'Found {current_count} comparable sales'}
        elif current_count < target_count:
            return {
                'status': 'loosen',
                'message': f'Only {current_count} comparables found. Consider loosening criteria.',
                'suggestions': [
                    'Increase land area range to ±30%',
                    'Increase floor area range to ±30%',
                    'Extend sale date range to 18 months',
                    'Relax bedroom/bathroom requirements'
                ]
            }
        else:
            return {
                'status': 'tighten',
                'message': f'Found {current_count} comparables. Consider tightening criteria.',
                'suggestions': [
                    'Reduce land area range to ±15%',
                    'Reduce floor area range to ±15%',
                    'Limit sale date range to 6 months',
                    'Strict bedroom/bathroom matching'
                ]
            }
