from decimal import Decimal, ROUND_HALF_UP
from typing import Union

TW_PRECISION = Decimal('0.01')

def to_decimal(val: Union[float, int, str, Decimal, None]) -> Decimal:
    """Safely converts any numeric value to Decimal with 2 decimal places."""
    if val is None:
        return Decimal('0.00')
    if isinstance(val, Decimal):
        return val.quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)

def calculate_line_item(
    quantity: int,
    unit_price: Union[float, int, str, Decimal],
    discount_per_unit: Union[float, int, str, Decimal] = 0,
    tax_rate: Union[float, int, str, Decimal] = 0.18 # e.g. 0.18 for 18%
) -> dict:
    """
    Computes exact line items:
    Line Subtotal = Quantity × Unit Price
    Total Line Discount = Quantity × Discount Per Unit
    Taxable Amount = Line Subtotal - Total Line Discount
    CGST (half of tax) = Taxable Amount × (tax_rate / 2)
    SGST (half of tax) = Taxable Amount × (tax_rate / 2)
    Total Tax = CGST + SGST
    Line Final Total = Taxable Amount + Total Tax
    """
    qty = Decimal(quantity)
    u_price = to_decimal(unit_price)
    disc_u = to_decimal(discount_per_unit)
    t_rate = Decimal(str(tax_rate))
    
    line_subtotal = (qty * u_price).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    line_discount = (qty * disc_u).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    
    # Cap discount at line subtotal
    if line_discount > line_subtotal:
        line_discount = line_subtotal
        
    taxable_amount = (line_subtotal - line_discount).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    
    half_rate = t_rate / Decimal('2.0')
    cgst = (taxable_amount * half_rate).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    sgst = (taxable_amount * half_rate).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    total_tax = (cgst + sgst).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    
    line_final = (taxable_amount + total_tax).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
    
    return {
        "quantity": quantity,
        "unit_price": u_price,
        "discount_per_unit": disc_u,
        "line_subtotal": line_subtotal,
        "line_discount": line_discount,
        "taxable_amount": taxable_amount,
        "tax_rate": t_rate,
        "cgst": cgst,
        "sgst": sgst,
        "total_tax": total_tax,
        "line_final": line_final
    }
