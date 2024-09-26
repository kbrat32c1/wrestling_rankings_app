import math

class Glicko2:
    def __init__(self, tau=0.5):
        self.tau = tau
        self.default_rating = 1500
        self.default_rd = 350
        self.default_vol = 0.06

    def g(self, rd):
        return 1 / math.sqrt(1 + (3 * rd**2) / (math.pi**2))

    def E(self, rating, opp_rating, opp_rd):
        return 1 / (1 + math.exp(-self.g(opp_rd) * (rating - opp_rating) / 400))

    def update_rating(self, rating, rd, vol, outcomes):
        # Convert rating and RD to Glicko-2 scale
        mu = (rating - self.default_rating) / 173.7178
        phi = rd / 173.7178

        v_inv = 0
        delta = 0
        for opp_r, opp_rd, score in outcomes:
            opp_mu = (opp_r - self.default_rating) / 173.7178
            opp_phi = opp_rd / 173.7178
            g_phi = self.g(opp_phi)
            E = self.E(mu, opp_mu, opp_phi)
            v_inv += g_phi**2 * E * (1 - E)
            delta += g_phi * (score - E)
        
        v = 1 / v_inv if v_inv != 0 else 0
        delta *= v

        a = math.log(vol**2)
        def f(x):
            ex = math.exp(x)
            num1 = ex * (delta**2 - phi**2 - v - ex)
            den1 = 2 * (phi**2 + v + ex)**2
            return (num1 / den1) - ((x - a) / self.tau**2)

        epsilon = 0.000001
        A = a
        B = 0
        if delta**2 > phi**2 + v:
            B = math.log(delta**2 - phi**2 - v)
        else:
            k = 1
            while f(a - k * self.tau) < 0:
                k += 1
            B = a - k * self.tau

        fa = f(A)
        fb = f(B)
        while abs(B - A) > epsilon:
            C = A + (A - B) * fa / (fb - fa)
            fc = f(C)
            if fc * fb < 0:
                A = B
                fa = fb
            else:
                fa = fa / 2
            B = C
            fb = fc

        new_vol = math.exp(A / 2)

        phi_star = math.sqrt(phi**2 + new_vol**2)
        new_phi = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
        new_mu = mu + new_phi**2 * delta

        new_rating = 173.7178 * new_mu + self.default_rating
        new_rd = 173.7178 * new_phi

        return new_rating, new_rd, new_vol