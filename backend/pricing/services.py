def get_selling_price(product, batch=None):
    """
    Central pricing logic.
    This is the ONLY place where price should be decided.
    """

    if batch:
        return batch.selling_price

    # Future extension
    # price = Price.objects.filter(...).first()
    # return price.base_price

    raise Exception("No pricing available")