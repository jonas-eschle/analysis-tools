#ifndef ROO_IPATIAHELPERS
#define ROO_IPATIAHELPERS

#include <math.h>

#include "TMath.h"
#include "Math/SpecFunc.h"
#include "Math/SpecFuncMathMore.h"

const Double_t sq2pi = TMath::Sqrt(2.*TMath::ACos(-1.));
const Double_t sq2pi_inv = 1./sq2pi;
const Double_t logsq2pi = TMath::Log(sq2pi);
const Double_t log_de_2 = TMath::Log(2.);

Double_t low_x_BK(Double_t nu,Double_t x){
  return TMath::Gamma(nu)*TMath::Power(2.,nu-1.)*TMath::Power(x,-nu);
}


Double_t low_x_LnBK(Double_t nu, Double_t x){
  return TMath::Log(TMath::Gamma(nu)) + (nu-1.)*log_de_2 - nu * TMath::Log(x);
}

Double_t BK(Double_t ni, Double_t x) {
  Double_t nu = TMath::Abs(ni);
  if ( x < 1.e-06 && nu > 0.) return low_x_BK(nu,x);
  if ( x < 1.e-04 && nu > 0. && nu < 55.) return low_x_BK(nu,x);
  if ( x < 0.1 && nu >= 55.) return low_x_BK(nu,x);

  //return gsl_sf_bessel_Knu(nu, x);
  return ROOT::Math::cyl_bessel_k(nu, x);
}

Double_t LnBK(double ni, double x) {
  Double_t nu = TMath::Abs(ni);
  if ( x < 1.e-06 && nu > 0.) return low_x_LnBK(nu,x);
  if ( x < 1.e-04 && nu > 0. && nu < 55.) return low_x_LnBK(nu,x);
  if ( x < 0.1 && nu >= 55.) return low_x_LnBK(nu,x);

  //return gsl_sf_bessel_lnKnu(nu, x);
  return TMath::Log(ROOT::Math::cyl_bessel_k(nu, x));
}


Double_t LogEval(Double_t d, Double_t l, Double_t alpha, Double_t beta, Double_t delta) {
  //Double_t d = x-mu;
  //Double_t sq2pi = TMath::Sqrt(2*TMath::ACos(-1));
  Double_t gamma = alpha;//TMath::Sqrt(alpha*alpha-beta*beta);
  Double_t dg = delta*gamma;
  Double_t thing = delta*delta + d*d;
  Double_t logno = l*TMath::Log(gamma/delta) - logsq2pi -LnBK(l, dg);

  return TMath::Exp(logno + beta*d +(0.5-l)*(TMath::Log(alpha)-0.5*TMath::Log(thing)) + LnBK(l-0.5,alpha*TMath::Sqrt(thing)));// + TMath::Log(TMath::Abs(beta)+0.0001) );

}


Double_t diff_eval(Double_t d, Double_t l, Double_t alpha, Double_t beta, Double_t delta){
  //Double_t sq2pi = TMath::Sqrt(2*TMath::ACos(-1));
  //Double_t cons1 = 1./sq2pi;
  Double_t gamma = alpha;// TMath::Sqrt(alpha*alpha-beta*beta);
  Double_t dg = delta*gamma;
  //Double_t mu_ = mu;// - delta*beta*BK(l+1,dg)/(gamma*BK(l,dg));
  //Double_t d = x-mu;
  Double_t thing = delta*delta + d*d;
  Double_t sqthing = TMath::Sqrt(thing);
  Double_t alphasq = alpha*sqthing;
  Double_t no = TMath::Power(gamma/delta,l)/BK(l,dg)*sq2pi_inv;
  Double_t ns1 = 0.5-l;
  //Double_t cheat = TMath::Exp(beta*d);//*(TMath::Abs(beta) + 1e-04);
  //Double_t cheat = TMath::Exp(beta*d);//*(TMath::Abs(beta) + 0.0001);

  //no =  no*TMath::Power(alpha, ns1 )*TMath::Power(thing, 0.5*l - 5.0/4.0)*0.5*cheat;//TMath::Exp(beta*d);

  //return no*(-alphasq*d* (BK(l - 3.0/2.0, alphasq) - BK(l + 0.5, alphasq)) + (2*beta*thing + 2*d*l - d)*BK(-ns1, alphasq));
  //return no*TMath::Power(alpha, -l + 1.0/2.0)*TMath::Power(thing, l/2 - 5.0/4.0)*(-d*alphasq*BK(l - 3.0/2.0, alphasq) - d*alphasq*BK(l + 1.0/2.0, alphasq) + 2*beta*thing*BK(l - 0.5, alphasq) + 2*d*l*BK(l - 0.5, alphasq) - d*BK(l - 0.5, alpha*sqthing))*TMath::Exp(beta*d)/2;

  return no*TMath::Power(alpha, ns1)*TMath::Power(thing, l/2. - 1.25)*(-d*alphasq*(BK(l - 1.5, alphasq) + BK(l + 0.5, alphasq)) + (2.*(beta*thing + d*l) - d)*BK(ns1, alphasq))*TMath::Exp(beta*d)/2.;
}

#endif

